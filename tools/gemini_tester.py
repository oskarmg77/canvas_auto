# tools/gemini_tester.py

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
import json
import sys
import os
import fitz  # PyMuPDF

# --- Añadir el directorio raíz al path para poder importar 'app' ---
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from app.api.gemini_client import GeminiClient
from app.utils import config_manager
from app.utils.logger_config import logger

class GeminiTesterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Herramienta de Prueba - Gemini API")
        self.geometry("800x700")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Frame de selección de archivos ---
        file_frame = ctk.CTkFrame(self)
        file_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        file_frame.grid_columnconfigure(1, weight=1)

        # Paths de los archivos
        self.pdf_path = None
        self.rubric_path = None

        # Widgets de selección
        ctk.CTkButton(file_frame, text="1. Seleccionar PDF del Alumno", command=self._select_pdf).grid(row=0, column=0, padx=5, pady=5)
        self.pdf_label = ctk.CTkLabel(file_frame, text="No seleccionado", anchor="w")
        self.pdf_label.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkButton(file_frame, text="2. Seleccionar Rúbrica JSON", command=self._select_rubric).grid(row=1, column=0, padx=5, pady=5)
        self.rubric_label = ctk.CTkLabel(file_frame, text="No seleccionado", anchor="w")
        self.rubric_label.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # --- Frame de resultados ---
        result_frame = ctk.CTkFrame(self)
        result_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        result_frame.grid_columnconfigure(0, weight=1)
        result_frame.grid_rowconfigure(0, weight=1)

        self.result_textbox = ctk.CTkTextbox(result_frame, wrap="word")
        self.result_textbox.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # --- Botón de ejecución ---
        ctk.CTkButton(self, text="Ejecutar Evaluación", command=self._run_evaluation, height=40).grid(row=2, column=0, padx=10, pady=10, sticky="ew")

    def _select_pdf(self):
        path = filedialog.askopenfilename(title="Selecciona el PDF a evaluar", filetypes=[("PDF files", "*.pdf")])
        if path:
            self.pdf_path = Path(path)
            self.pdf_label.configure(text=str(self.pdf_path))

    def _select_rubric(self):
        path = filedialog.askopenfilename(title="Selecciona la rúbrica JSON", filetypes=[("JSON files", "*.json")])
        if path:
            self.rubric_path = Path(path)
            self.rubric_label.configure(text=str(self.rubric_path))

    def _run_evaluation(self):
        if not all([self.pdf_path, self.rubric_path]):
            messagebox.showwarning("Archivos Faltantes", "Por favor, selecciona el PDF y la Rúbrica.")
            return

        self.result_textbox.delete("1.0", "end")
        self.result_textbox.insert("end", "Iniciando proceso...\n\n")
        self.update_idletasks()

        try:
            # 1. Cargar clave de API
            self.result_textbox.insert("end", "Cargando credenciales desde config.json...\n")
            credentials = config_manager.load_credentials()
            if not credentials:
                messagebox.showerror("Error", "No se pudo cargar 'config.json'.\nAsegúrate de que existe en la raíz del proyecto.")
                return
            gemini_key = credentials.get("gemini_api_key")
            if not gemini_key:
                messagebox.showerror("Error", "No se encontró 'gemini_api_key' en el archivo de configuración.")
                return

            # 2. Inicializar cliente
            self.result_textbox.insert("end", "Inicializando cliente de Gemini...\n")
            gemini_client = GeminiClient(gemini_key)
            if gemini_client.error_message:
                raise Exception(f"Error al inicializar el cliente: {gemini_client.error_message}")

            # 3. Extraer texto del PDF
            self.result_textbox.insert("end", f"Extrayendo texto e imágenes de {self.pdf_path.name}...\n")
            submission_content = self._extract_multimodal_content_from_pdf(self.pdf_path)
            if not submission_content:
                raise Exception("No se pudo extraer contenido del PDF o está vacío.")

            # 4. Cargar rúbrica
            self.result_textbox.insert("end", "Cargando rúbrica...\n")
            with self.rubric_path.open("r", encoding="utf-8") as f:
                rubric_data = json.load(f)

            # 5. Evaluar
            self.result_textbox.insert("end", "Enviando a Gemini para evaluación... (esto puede tardar)\n\n")
            # NOTA: Asegúrate de que tu `GeminiClient.evaluate_submission` esté preparado
            # para recibir una lista de contenidos (texto/imágenes) y usar el modelo 'gemini-pro-vision'.
            # La llamada ahora envía el contenido multimodal en lugar de solo texto.
            evaluation_result = gemini_client.evaluate_submission(submission_content, rubric_data)

            # 6. Mostrar resultados
            if evaluation_result:
                formatted_json = json.dumps(evaluation_result, indent=4, ensure_ascii=False)
                formatted_text = self._format_evaluation_for_txt(evaluation_result)

                output = (
                    "--- EVALUACIÓN COMPLETADA ---\n\n"
                    "--- FORMATO DE TEXTO LEGIBLE ---\n"
                    f"{formatted_text}\n\n"
                    "--------------------------------\n\n"
                    "--- JSON CRUDO RECIBIDO ---\n"
                    f"{formatted_json}"
                )
                self.result_textbox.insert("end", output)
            else:
                raise Exception(f"La evaluación falló. Mensaje del cliente: {gemini_client.error_message}")

        except Exception as e:
            error_message = f"--- ERROR ---\n{e}"
            self.result_textbox.insert("end", error_message)
            logger.error(f"Error en la herramienta de prueba: {e}", exc_info=True)

    def _extract_multimodal_content_from_pdf(self, pdf_path: Path) -> list | None:
        """Extrae el texto y las imágenes de un PDF página por página."""
        try:
            content_parts = []
            with fitz.open(pdf_path) as doc:
                for page_num, page in enumerate(doc):
                    # Añadir el texto de la página
                    content_parts.append(page.get_text())

                    # Extraer y añadir las imágenes de la página
                    image_list = page.get_images(full=True)
                    for img_index, img in enumerate(image_list):
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]
                        mime_type = f"image/{image_ext}"
                        
                        # Añadir la imagen en el formato que espera la API de Gemini
                        content_parts.append({"mime_type": mime_type, "data": image_bytes})
            return content_parts if content_parts else None
        except Exception as e:
            logger.error(f"No se pudo extraer contenido multimodal del PDF {pdf_path}: {e}")
            return None

    def _format_evaluation_for_txt(self, evaluation_data: dict) -> str:
        if not evaluation_data or "evaluacion" not in evaluation_data:
            return "No se pudo generar el resumen de la evaluación."
        lines = []
        total_score = 0.0
        for criterion in evaluation_data.get("evaluacion", []):
            lines.append(f"--- CRITERIO: {criterion.get('criterio_descripcion', 'N/A')} ---")
            score = criterion.get('puntuacion_obtenida', 0)
            lines.append(f"Puntuación: {score}")
            lines.append(f"Comentario: {criterion.get('comentario_profesor', 'Sin comentarios.')}")
            lines.append("")
            try:
                total_score += float(score)
            except (ValueError, TypeError):
                pass
        lines.insert(0, f"PUNTUACIÓN TOTAL ESTIMADA: {total_score}\n")
        return "\n".join(lines)

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    app = GeminiTesterApp()
    app.mainloop()