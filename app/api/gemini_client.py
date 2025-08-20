import google.generativeai as genai
import json
from PIL import Image


# Excepción personalizada para errores de límite de velocidad de la API
class RateLimitException(Exception):
    """Excepción personalizada para errores de límite de velocidad de la API."""
    pass


class GeminiClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.error_message = None
        self.model = None
        self._configure()

    def _configure(self):
        """Configura la API de Gemini y el modelo."""
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-pro-vision')
        except Exception as e:
            self.error_message = f"Error al configurar Gemini: {e}"

    def _split_content_into_chunks(self, content, chunk_size=7000):
        """Divide el contenido de texto en trozos más pequeños para no exceder el límite de tokens."""
        # Esta es una implementación simple. Se podría mejorar para no cortar en medio de frases.
        return [content[i:i + chunk_size] for i in range(0, len(content), chunk_size)]

    def evaluate_submission(self, submission_content: list, rubric_data: dict):
        """
        Evalúa una entrega, manejando documentos largos a través de "chunking".
        1. Divide el texto en trozos.
        2. Evalúa cada trozo (junto con las imágenes en el primer trozo).
        3. Sintetiza los resultados en una evaluación final.
        """
        if not self.model:
            self.error_message = "El modelo Gemini no está inicializado."
            return None

        text_content = "".join(part for part in submission_content if isinstance(part, str))
        image_parts = [part for part in submission_content if isinstance(part, Image.Image)]

        text_chunks = self._split_content_into_chunks(text_content)
        partial_evaluations = []

        # 1. Evaluar cada trozo
        for i, chunk in enumerate(text_chunks):
            try:
                prompt = self._construct_chunk_prompt(chunk, rubric_data, i + 1, len(text_chunks))
                # Las imágenes solo se envían con el primer trozo para evitar redundancia
                content_for_api = [prompt] + image_parts if i == 0 else [prompt]
                
                response = self.model.generate_content(content_for_api)
                partial_evaluations.append(response.text)

            except Exception as e:
                if "429" in str(e):  # Error de límite de peticiones
                    raise RateLimitException("Límite de API alcanzado.")
                self.error_message = f"Error en la API de Gemini al evaluar el trozo {i + 1}: {e}"
                return None

        # 2. Sintetizar los resultados
        if not partial_evaluations:
            self.error_message = "No se generaron evaluaciones parciales."
            return None

        try:
            if len(partial_evaluations) == 1:
                # Si solo hubo un trozo, la evaluación ya es la final, solo se reformatea
                synthesis_prompt = self._construct_final_synthesis_prompt_from_single(partial_evaluations[0], rubric_data)
            else:
                # Si hubo múltiples trozos, se consolidan
                synthesis_prompt = self._construct_synthesis_prompt(partial_evaluations, rubric_data)
            
            final_response = self.model.generate_content(synthesis_prompt)
            # Limpiar y cargar la respuesta JSON
            cleaned_json = final_response.text.strip().lstrip('```json').rstrip('```')
            return json.loads(cleaned_json)

        except RateLimitException:
             raise # Propagar la excepción de límite de peticiones
        except Exception as e:
            self.error_message = f"Error en la síntesis final: {e}. Respuesta recibida: {final_response.text if 'final_response' in locals() else 'N/A'}"
            return None

    def _construct_chunk_prompt(self, chunk, rubric_data, chunk_num, total_chunks):
        return f"""
        Rol: Eres un asistente evaluador. Estás analizando una parte de un trabajo más grande.
        Objetivo: Evalúa SOLO este fragmento del trabajo del alumno basándote en la rúbrica. Proporciona notas breves y observaciones para cada criterio.
        Importante: Esta es la parte {chunk_num} de {total_chunks}. NO des una puntuación final, solo observaciones sobre ESTE fragmento.

        Rúbrica de evaluación:
        {json.dumps(rubric_data, indent=2)}

        Fragmento del trabajo del alumno:
        {chunk}
        """

    def _construct_synthesis_prompt(self, partial_evaluations, rubric_data):
        evaluations_text = "\\n\\n---\\n\\n".join(f"Evaluación Parcial {i+1}:\\n{text}" for i, text in enumerate(partial_evaluations))
        return f"""
        Rol: Eres un profesor supervisor. Has recibido varias evaluaciones parciales del trabajo de un alumno.
        Objetivo: Consolida estas evaluaciones en un único informe final en formato JSON.
        Instrucciones: Lee las evaluaciones parciales y, para cada criterio de la rúbrica, genera una puntuación final y un comentario constructivo que resuma los hallazgos.
        El resultado DEBE ser un único objeto JSON, sin texto o formato adicional como \`\`\`json.

        Rúbrica original:
        {json.dumps(rubric_data, indent=2)}

        Evaluaciones Parciales:
        {evaluations_text}

        Genera el JSON final consolidado.
        """

    def _construct_final_synthesis_prompt_from_single(self, single_evaluation, rubric_data):
        return f"""
        Rol: Eres un profesor. Has recibido una evaluación del trabajo de un alumno.
        Objetivo: Formatear la evaluación en un informe final JSON.
        Instrucciones: Basándote en la evaluación, genera para cada criterio de la rúbrica una puntuación final y un comentario.
        El resultado DEBE ser un único objeto JSON, sin texto o formato adicional como \`\`\`json.

        Rúbrica original:
        {json.dumps(rubric_data, indent=2)}

        Evaluación del trabajo:
        {single_evaluation}

        Genera el JSON final.
        """