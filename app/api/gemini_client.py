"""
HybridEvaluator: fusión de los dos enfoques
- Soporta entrada multimodal (texto + imágenes PIL) y PDFs (por páginas con PyMuPDF/fitz)
- Reintentos con backoff exponencial + logging opcional
- Configuración de generación y safety explícitas
- Ensambla resultados por chunk/página y sintetiza a JSON validado (dict)

Requisitos (opcionales según el uso):
  pip install google-generativeai pillow PyMuPDF

Nota: Sustituye `YOUR_API_KEY` por tu clave o pásala al constructor.
"""
from __future__ import annotations

import io
from dataclasses import asdict, dataclass
from typing import List, Optional, Any, Dict, Union, Tuple
import json
import logging
import math
import os
import re
import time

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover
    genai = None  # Permite cargar el módulo aunque no esté instalado en el entorno

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None

try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover
    fitz = None


@dataclass
class GenerationConfig:
    temperature: float = 0.2
    top_p: float = 0.9
    top_k: int = 32
    max_output_tokens: int = 2048


DEFAULT_SAFETY = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUAL", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]


class HybridEvaluator:
    """Cliente unificado para evaluaciones con Gemini (texto/visión) y PDFs.

    - evaluate_mixed(text, images)
    - evaluate_pdf(pdf_path)

    Devuelve siempre un dict (JSON) validado. Lanza excepción si no es posible construir JSON.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        text_model: str = "gemini-1.5-pro",
        vision_model: str = "gemini-1.5-flash",  # rápido y multimodal; ajusta si lo prefieres
        gen: Optional[GenerationConfig] = None,
        safety: Optional[List[dict]] = None,
        logger: Optional[logging.Logger] = None,
        max_retries: int = 4,
        base_delay: float = 1.2,
        chunk_chars: int = 7000,
    ) -> None:
        if genai is None:
            raise ImportError("Falta google-generativeai. Instala con: pip install google-generativeai")

        # Prioridad: 1. Argumento directo, 2. Variables de entorno
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "No se encontró la API Key de Gemini. Por favor, configúrala en 'config.json' (con la clave 'gemini_api_key') "
                "o como variable de entorno ('GOOGLE_API_KEY')."
            )
        genai.configure(api_key=self.api_key)

        self.text_model_name = text_model
        self.vision_model_name = vision_model
        self.gen_cfg = gen or GenerationConfig()
        self.safety = safety or DEFAULT_SAFETY
        self.logger = logger or logging.getLogger(__name__)
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.chunk_chars = chunk_chars

        # Modelos
        self._text_model = genai.GenerativeModel(self.text_model_name)
        self._vision_model = genai.GenerativeModel(self.vision_model_name)

    # -------------------------- PÚBLICO ----------------------------------
    def evaluate_mixed(self, text: str, images: Optional[List["Image.Image"]] = None, schema_hint: Optional[str] = None) -> Dict[str, Any]:
        """Evalúa entrada multimodal en chunks de texto (+ imágenes solo en el primer chunk).
        """
        chunks = self._chunk_text(text, self.chunk_chars)
        partials: List[Dict[str, Any]] = []

        for idx, chunk in enumerate(chunks):
            parts = []
            if idx == 0 and images:
                # Adjuntamos imágenes al primer turno
                for img in images:
                    parts.append(img)
            parts.append(self._build_chunk_prompt(chunk, idx + 1, len(chunks), schema_hint))

            resp_text = self._call_with_retry(self._vision_model, parts)
            partials.append(self._json_from_text(resp_text))

        # Síntesis final
        synth_prompt = self._build_synthesis_prompt(partials, schema_hint)
        final_text = self._call_with_retry(self._text_model, synth_prompt)
        return self._json_from_text(final_text)

    def evaluate_pdf(self, pdf_path: str, schema_hint: Optional[str] = None, pages: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Evalúa un PDF completo en una sola llamada a la API.
        Extrae texto e imágenes de todas las páginas y las envía juntas.
        Si `pages` es None, procesa todas las páginas.
        """
        if fitz is None:
            raise ImportError("Falta PyMuPDF. Instala con: pip install PyMuPDF")
 
        doc = fitz.open(pdf_path)
        total = doc.page_count
        page_ids = pages or list(range(total))
 
        # --- NUEVA ESTRATEGIA: Recopilar todo el contenido primero ---
        all_parts: List[Any] = []
        full_text = ""

        for i in page_ids:
            page = doc.load_page(i)
            page_text = page.get_text("text") or ""
            full_text += f"\n\n--- PÁGINA {i+1}/{total} ---\n{page_text}"

            if Image:  # Comprueba si PIL/Pillow se importó correctamente
                try:
                    pix = page.get_pixmap()
                    img_bytes = pix.tobytes("png")
                    pil_img = Image.open(io.BytesIO(img_bytes))
                    all_parts.append(pil_img)
                except Exception as e:
                    self.logger.warning(f"No se pudo procesar la imagen de la página {i+1}: {e}")

        # Añadimos el prompt y el texto completo al principio de la lista de partes
        prompt = self._build_page_prompt(full_text, 1, 1, schema_hint) # Adaptamos el prompt
        all_parts.insert(0, prompt)

        # --- UNA ÚNICA LLAMADA A LA API ---
        final_text = self._call_with_retry(self._vision_model, all_parts)
        return self._json_from_text(final_text)

    # -------------------------- INTERNOS ---------------------------------
    def _call_with_retry(self, model, parts_or_text: Union[str, List[Any]]) -> str:
        """Llama al modelo con reintentos y backoff. Acepta string o lista multimodal."""
        last_err: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                if isinstance(parts_or_text, list):
                    resp = model.generate_content(parts_or_text, generation_config=self.gen_cfg.__dict__, safety_settings=self.safety)
                else:
                    resp = model.generate_content(parts_or_text, generation_config=self.gen_cfg.__dict__, safety_settings=self.safety)
                if hasattr(resp, "text") and resp.text:
                    return resp.text
                # Algunas versiones exponen candidatos
                if getattr(resp, "candidates", None):
                    text = resp.candidates[0].content.parts[0].text
                    if text:
                        return text
                raise RuntimeError("Respuesta sin texto del modelo")
            except Exception as e:  # pragma: no cover
                last_err = e
                msg = str(e)
                self.logger.warning("Intento %d/%d falló: %s", attempt, self.max_retries, msg)
                # Heurística de rate limit
                if any(code in msg for code in ["429", "rate", "Rate"]):
                    delay = self.base_delay * (2 ** (attempt - 1))
                else:
                    delay = min(self.base_delay * (1.5 ** (attempt - 1)), 8.0)
                time.sleep(delay)
        # Si llegamos aquí, no hubo éxito
        raise RuntimeError(f"Fallo tras reintentos: {last_err}")

    def _chunk_text(self, text: str, size: int) -> List[str]:
        text = text or ""
        if len(text) <= size:
            return [text]
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            chunks.append(text[start:end])
            start = end
        return chunks

    def _build_chunk_prompt(self, chunk: str, idx: int, total: int, schema_hint: Optional[str]) -> str:
        return (
            "Eres un evaluador. Analiza este fragmento de una entrega (" f"chunk {idx}/{total})."
            + "\n\nCONTENIDO:\n" + chunk.strip() +
            "\n\nDevuelve SOLO JSON válido y minificado (sin explicaciones). "
            + (f"Ajusta al siguiente esquema si aplica: {schema_hint}\n" if schema_hint else "")
            + "Usa campos consistentes entre chunks."
        )

    def _build_page_prompt(self, page_text: str, page_no: int, total_pages: int, schema_hint: Optional[str]) -> str:
        return (
            "Eres un evaluador. Analiza el siguiente documento PDF completo (imágenes adjuntas y texto a continuación).\n\n"
            "CONTENIDO DEL TEXTO EXTRAÍDO DEL PDF:\n" + page_text.strip() +
            "\n\nDevuelve SOLO JSON válido y minificado (sin explicaciones). "
            + (f"Ajusta al siguiente esquema si aplica: {schema_hint}\n" if schema_hint else "")
        )

    def _build_synthesis_prompt(self, partials: List[Dict[str, Any]], schema_hint: Optional[str]) -> str:
        return (
            "Combina de forma consistente los siguientes JSON parciales en un ÚNICO JSON final, "
            "deduplicando y resolviendo conflictos (preferir evidencias más completas).\n\nPARCIALES:\n"
            + json.dumps(partials, ensure_ascii=False)
            + "\n\nDevuelve SOLO JSON válido y minificado. "
            + (f"Ajusta al siguiente esquema si aplica: {schema_hint}" if schema_hint else "")
        )

    # -------------------------- UTILIDADES JSON --------------------------
    _FENCE_RE = re.compile(r"^```(?:json)?\n|\n```$", re.IGNORECASE)

    def _json_from_text(self, text: str) -> Dict[str, Any]:
        """Intenta parsear texto a JSON dict. Limpia fences y corrige algunos errores comunes.
        Lanza ValueError si no puede devolver un dict.
        """
        if text is None:
            raise ValueError("Respuesta vacía del modelo")
        cleaned = text.strip()
        cleaned = self._FENCE_RE.sub("", cleaned)
        cleaned = cleaned.strip()

        # Heurísticas: si empieza con algo que no es {, intenta localizar el primer {...}
        if not cleaned.startswith("{"):
            m = re.search(r"\{[\s\S]*\}\s*$", cleaned)
            if m:
                cleaned = m.group(0)

        try:
            data = json.loads(cleaned)
        except Exception as e:
            # Último intento: arreglar comas colgantes y true/false/none estilo Python
            fixed = cleaned
            fixed = re.sub(r",\s*([}\]])", r"\1", fixed)
            fixed = re.sub(r"\bTrue\b", "true", fixed)
            fixed = re.sub(r"\bFalse\b", "false", fixed)
            fixed = re.sub(r"\bNone\b", "null", fixed)
            data = json.loads(fixed)

        if not isinstance(data, dict):
            # En caso de lista raíz, lo envolvemos en un objeto estándar
            return {"items": data}
        return data


# ------------------------------ EJEMPLO ---------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    evaluator = HybridEvaluator(api_key=os.getenv("GOOGLE_API_KEY", "YOUR_API_KEY"))

    # Ejemplo multimodal
    sample_text = """Resumen del ejercicio 1 y 2... (texto largo)"""
    images = []
    if Image:
        # Crea una imagen en blanco de ejemplo (opcional)
        img = Image.new("RGB", (200, 100), color=(240, 240, 240))
        images.append(img)
    try:
        result = evaluator.evaluate_mixed(sample_text, images, schema_hint="{'resumen': str, 'puntos': [str]} ")
        print("Resultado multimodal:", json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print("Multimodal falló (probablemente por API key de ejemplo):", e)

    # Ejemplo PDF (requiere PyMuPDF y un archivo real)
    pdf_demo = os.getenv("PDF_DEMO_PATH")
    if pdf_demo and os.path.exists(pdf_demo):
        try:
            result_pdf = evaluator.evaluate_pdf(pdf_demo, schema_hint="{'hallazgos': [str]}")
            print("Resultado PDF:", json.dumps(result_pdf, ensure_ascii=False, indent=2))
        except Exception as e:
            print("PDF falló:", e)
