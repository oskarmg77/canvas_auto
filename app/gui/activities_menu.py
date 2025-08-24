# app/gui/activities_menu.py

import customtkinter as ctk
from tkinter import messagebox, filedialog

from app.utils.event_logger import log_action
from pathlib import Path
from app.utils.logger_config import logger
import os
import threading
import urllib.parse
import json
import queue
import csv
import concurrent.futures
import time
try:
    import google.generativeai as genai
except ImportError:
    genai = None

import re

# Diccionario para los tipos de entrega. Clave: API, Valor: Texto en GUI
SUBMISSION_TYPES = {
    "online_upload": "Subir archivo",
    "online_text_entry": "Entrada de texto",
    "online_url": "URL de un sitio web",
}

class ActivitiesMenu(ctk.CTkFrame):
    def __init__(self, parent, client, gemini_evaluator, course_id, main_window):
        super().__init__(parent)
        self.client = client
        self.gemini_evaluator = gemini_evaluator
        self.course_id = course_id
        self.main_window = main_window # Referencia a la ventana principal para usar la barra de estado
        self.submission_checkboxes = {}  # Para almacenar las variables de los checkboxes
        self.assignments = {}
        self.assignment_buttons = {}
        self.selected_assignment_id = None
        self.active_thread = None  # Para controlar el hilo de descarga
        self.queue = queue.Queue() # Cola para comunicación thread-safe
        self.stop_polling = False # Flag para detener el sondeo de la cola

        back_button = ctk.CTkButton(self, text="< Volver al Menú Principal", command=self.main_window.show_main_menu)
        back_button.pack(anchor="nw", padx=10, pady=10)

        container = ctk.CTkFrame(self)
        container.pack(expand=True, fill="both", padx=10, pady=(0, 10))

        self.tab_view = ctk.CTkTabview(container, anchor="w")
        self.tab_view.pack(expand=True, fill="both")

        self.tab_view.add("Crear Actividad")
        self.tab_view.add("Descargar Entregas")
        self.setup_activity_tab()
        self.setup_download_tab()

    def setup_activity_tab(self):
        activity_tab = self.tab_view.tab("Crear Actividad")
        activity_tab.grid_columnconfigure(1, weight=1)

        # --- Nombre y Puntos ---
        name_label = ctk.CTkLabel(activity_tab, text="Nombre de la Actividad:")
        name_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        self.activity_name_entry = ctk.CTkEntry(activity_tab)
        self.activity_name_entry.grid(row=0, column=1, padx=20, pady=(20, 10), sticky="ew")

        points_label = ctk.CTkLabel(activity_tab, text="Puntos Posibles:")
        points_label.grid(row=1, column=0, padx=20, pady=10, sticky="w")
        self.activity_points_entry = ctk.CTkEntry(activity_tab)
        self.activity_points_entry.grid(row=1, column=1, padx=20, pady=10, sticky="w")

        # --- Tipos de Entrega (Dinámico) ---
        submission_label = ctk.CTkLabel(activity_tab, text="Tipos de Entrega Online:")
        submission_label.grid(row=2, column=0, padx=20, pady=10, sticky="nw")
        submission_frame = ctk.CTkFrame(activity_tab)
        submission_frame.grid(row=2, column=1, padx=20, pady=10, sticky="w")

        for key, text in SUBMISSION_TYPES.items():
            var = ctk.StringVar(value="0")
            chk = ctk.CTkCheckBox(submission_frame, text=f"{text} ({key})", variable=var, onvalue="1", offvalue="0")
            chk.pack(anchor="w", padx=10, pady=5)
            self.submission_checkboxes[key] = var

        # --- Descripción y Botón ---
        desc_label = ctk.CTkLabel(activity_tab, text="Descripción:")
        desc_label.grid(row=3, column=0, padx=20, pady=10, sticky="nw")
        self.activity_desc_textbox = ctk.CTkTextbox(activity_tab, height=150)
        self.activity_desc_textbox.grid(row=3, column=1, padx=20, pady=10, sticky="nsew")
        activity_tab.grid_rowconfigure(3, weight=1)

        create_button = ctk.CTkButton(activity_tab, text="Crear Actividad", command=self.handle_create_activity)
        create_button.grid(row=4, column=1, padx=20, pady=20, sticky="e")

    def setup_download_tab(self):
        download_tab = self.tab_view.tab("Descargar Entregas")
        download_tab.grid_columnconfigure(0, weight=1)
        download_tab.grid_rowconfigure(1, weight=1)

        info_frame = ctk.CTkFrame(download_tab)
        info_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        info_frame.grid_columnconfigure(0, weight=1)

        self.selected_assignment_label = ctk.CTkLabel(
            info_frame, text="Selecciona una actividad de la lista para ver detalles y descargar.", anchor="w"
        )
        self.selected_assignment_label.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

        # --- Frame para los botones de acción (Descargar / Evaluar) ---
        actions_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        actions_frame.grid(row=1, column=0, sticky="ew", pady=(5,0))

        self.download_button = ctk.CTkButton(
            actions_frame, text="Descargar Entregas", state="disabled",
            command=self._prompt_download_location
        )
        self.download_button.pack(side="left", padx=10)

        self.evaluate_button = ctk.CTkButton(
            actions_frame, text="Evaluar con IA (Gemini)", state="disabled",
            command=self._start_evaluation_thread
        )
        self.evaluate_button.pack(side="left", padx=10)

        # Frame para la lista de actividades
        self.assignments_frame = ctk.CTkScrollableFrame(download_tab, label_text="Actividades del Curso")
        self.assignments_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.assignments_frame.grid_columnconfigure(0, weight=1)
        
        # Mensaje de carga inicial en el frame
        self.loading_label = ctk.CTkLabel(self.assignments_frame, text="Cargando, por favor espera...")
        self.loading_label.pack(pady=20)

        # Iniciar la carga en un hilo para no bloquear la GUI
        threading.Thread(target=self._load_assignments, daemon=True).start()

    def _load_assignments(self):
        """Carga las actividades en un hilo secundario y actualiza la GUI."""
        self.after(0, self.main_window.update_status, "Cargando lista de actividades...")
        try:
            assignment_groups = self.client.get_assignment_groups_with_assignments(self.course_id)
            self.after(0, self._populate_assignments_list, assignment_groups)
            self.after(0, self.main_window.update_status, "Listo", 3000)
        except Exception as e:
            error_msg = f"No se pudieron cargar las actividades: {e}"
            logger.error(error_msg, exc_info=True)
            self.after(0, self.main_window.update_status, "Error al cargar actividades.", 5000)
            self.after(0, messagebox.showerror, "Error", error_msg)
            self.after(0, self.loading_label.configure, {"text": "Error al cargar."})

    def _populate_assignments_list(self, assignment_groups):
        """Puebla la lista de actividades en el hilo principal."""
        self.loading_label.pack_forget() # Ocultar el mensaje de "cargando"

        if not assignment_groups:
            no_groups_label = ctk.CTkLabel(self.assignments_frame, text="No se encontraron grupos de actividades.")
            no_groups_label.pack(pady=10)
            return

        for group in assignment_groups:
            group_label = ctk.CTkLabel(
                self.assignments_frame,
                text=group['name'],
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w"
            )
            group_label.pack(fill="x", padx=5, pady=(10, 5))

            assignments_in_group = group.get('assignments', [])
            if not assignments_in_group:
                no_assign_label = ctk.CTkLabel(
                    self.assignments_frame,
                    text=" (Sin actividades en este grupo)",
                    font=ctk.CTkFont(size=11, slant="italic"),
                    anchor="w"
                )
                no_assign_label.pack(fill="x", padx=20, pady=(0, 5))

            for assignment in assignments_in_group:
                assignment_id = assignment['id']
                self.assignments[assignment_id] = assignment
                btn = ctk.CTkButton(
                    self.assignments_frame,
                    text=assignment['name'],
                    command=lambda a_id=assignment_id: self._select_assignment(a_id)
                )
                btn.pack(fill="x", padx=(20, 5), pady=2)
                self.assignment_buttons[assignment_id] = btn

    def _enable_assignment_buttons(self, enable=True):
        """Helper para (des)activar los botones de actividad en el hilo principal."""
        state = "normal" if enable else "disabled"
        for btn in self.assignment_buttons.values():
            btn.configure(state=state)
        self.download_button.configure(state="disabled")
        self.evaluate_button.configure(state="disabled")

    def _select_assignment(self, assignment_id):
        """Se llama al pulsar un botón de actividad. Inicia la obtención de detalles."""
        if self.active_thread and self.active_thread.is_alive():
            messagebox.showwarning("Proceso en curso", "Espera a que termine el proceso actual.")
            return

        self.selected_assignment_id = assignment_id
        assignment_name = self.assignments[assignment_id]["name"]
        self.selected_assignment_label.configure(text=f"Actividad seleccionada: {assignment_name}")
        
        self.main_window.update_status("Obteniendo resumen de entregas...")
        self.main_window.show_progress_bar(indeterminate=True)
        logger.info(f"Actividad seleccionada: {assignment_name} (ID: {assignment_id}). Obteniendo resumen...")

        self._enable_assignment_buttons(False)

        self.active_thread = threading.Thread(target=self._fetch_and_prompt_download, args=(assignment_id,))
        self.active_thread.start()

    def _update_action_buttons(self, summary: dict):
        """Actualiza el estado de los botones de acción basado en el resumen."""
        self.download_button.configure(state="normal")
        
        # Activar el botón de evaluación solo si hay rúbrica y el cliente de Gemini está disponible
        if summary.get("has_rubric") and self.gemini_evaluator:
            self.evaluate_button.configure(state="normal")
        else:
            self.evaluate_button.configure(state="disabled")
            if not self.gemini_evaluator:
                self.main_window.update_status("Evaluación no disponible: Módulo Gemini no cargado.", 5000)
            elif not summary.get("has_rubric"):
                 self.main_window.update_status("Evaluación no disponible: La actividad no tiene rúbrica.", 5000)


    def _fetch_and_prompt_download(self, assignment_id):
        """Obtiene el resumen de la actividad y actualiza la UI."""
        try:
            summary = self.client.get_assignment_submission_summary(self.course_id, assignment_id)
            if not summary:
                raise Exception(self.client.error_message or "La API no devolvió un resumen.")

            # Guardamos el resumen para usarlo después
            self.assignments[assignment_id]['summary'] = summary

            def update_ui_on_main_thread():
                self.main_window.hide_progress_bar()
                self._enable_assignment_buttons(True)
                assignment_name = self.assignments[assignment_id]["name"]
                info_message = (
                    f"Actividad: {assignment_name}\n\n"
                    f"• Total de entregas: {summary['submission_count']}\n"
                    f"• Entregas con PDF (aprox): {summary['pdf_submission_count']}\n"
                    f"• Tiene rúbrica asociada: {'Sí' if summary['has_rubric'] else 'No'}"
                )
                self.selected_assignment_label.configure(text=info_message)
                self.main_window.update_status("Resumen cargado. Selecciona una acción.", 5000)
                self._update_action_buttons(summary)

            self.after(0, update_ui_on_main_thread)

        except Exception as e:
            logger.error(f"Error al obtener resumen de la actividad {assignment_id}: {e}")
            self.after(0, self._on_download_error, "Error al obtener el resumen de la actividad.")

    @log_action
    def _prompt_download_location(self):
        """Pide al usuario una carpeta y luego inicia la descarga."""
        if not self.selected_assignment_id: return

        assignment_id = self.selected_assignment_id
        summary = self.assignments[assignment_id].get('summary')
        if not summary:
            messagebox.showerror("Error", "No se ha cargado el resumen de la actividad.")
            return

        base_dir = filedialog.askdirectory(title="Selecciona la carpeta base para las descargas")
        if not base_dir:
            self.main_window.update_status("Descarga cancelada.", clear_after_ms=4000)
            return

        self._start_download_thread(assignment_id, summary, base_dir)

    def _start_download_thread(self, assignment_id, summary, base_dir):
        """Inicia el proceso de descarga de archivos en un nuevo hilo."""
        self.main_window.update_status("Iniciando descarga...")
        self.main_window.show_progress_bar() # Barra de progreso determinada
        self._enable_assignment_buttons(False)

        self.active_thread = threading.Thread(
            target=self._handle_download_submissions, args=(assignment_id, summary, base_dir)
        )
        self.active_thread.start()

    @log_action
    def _start_evaluation_thread(self):
        """Pide ubicación y comienza el hilo de evaluación con IA."""
        if not self.selected_assignment_id: return
        
        assignment_id = self.selected_assignment_id
        summary = self.assignments[assignment_id].get('summary')

        base_dir = filedialog.askdirectory(title="Selecciona la carpeta base para las descargas")
        if not base_dir:
            self.main_window.update_status("Evaluación cancelada.", clear_after_ms=4000)
            return

        # Limpiar la cola de mensajes antiguos antes de empezar un nuevo proceso
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except queue.Empty:
                break

        self.main_window.update_status("Iniciando evaluación con IA...")
        self.main_window.show_progress_bar()
        self._enable_assignment_buttons(False)

        self.active_thread = threading.Thread(
            target=self._handle_evaluation, args=(assignment_id, summary, base_dir)
        )
        self.active_thread.start()
        self.stop_polling = False # Asegurarse de que el sondeo esté activo
        self._process_queue() # Iniciar el procesador de la cola

    def _process_queue(self):
        """Procesa mensajes de la cola para actualizar la GUI de forma segura."""
        if self.stop_polling:
            return
        try:
            while not self.queue.empty():
                message_type, data = self.queue.get_nowait()

                if message_type == "update_status":
                    self.main_window.update_status(data[0], data[1] if len(data) > 1 else 0)
                elif message_type == "update_progress":
                    self.main_window.update_progress(data)
                elif message_type == "show_progress_bar":
                    self.main_window.show_progress_bar(**data)
                elif message_type == "hide_progress_bar":
                    self.main_window.hide_progress_bar()
                elif message_type == "evaluation_success":
                    self._on_evaluation_success(data)
                elif message_type == "evaluation_error":
                    self._on_download_error(data)
                elif message_type == "evaluation_finished":
                    self.stop_polling = True # Detener el sondeo
                    self._enable_assignment_buttons(True)
                    self.main_window.update_status("Proceso finalizado.", 5000)

        except queue.Empty:
            pass
        finally:
            if not self.stop_polling:
                self.after(100, self._process_queue) # Volver a comprobar en 100ms

    def _handle_evaluation(self, assignment_id, summary, base_dir):
        """Lógica de evaluación con Gemini usando la API de Archivos y de Lotes."""
        uploaded_files = {}  # {student_name: gemini_file_object} 
        try:
            # --- PREPARACIÓN ---
            assignment = self.assignments[assignment_id]
            course = self.client.get_course(self.course_id)
            course_abbreviation = self._create_abbreviation(course.name)
            assignment_abbreviation = self._create_abbreviation(assignment['name'])
            activity_path = Path(base_dir) / f"{self.course_id} - {course_abbreviation}" / f"{assignment_id} - {assignment_abbreviation}"
            activity_path.mkdir(parents=True, exist_ok=True)

            self.queue.put(("update_status", ("Descargando rúbrica...",)))
            rubric_path = activity_path / f"rubrica_{assignment_id}.json"
            if not self.client.export_rubric_to_json(self.course_id, summary["rubric_id"], rubric_path):
                raise Exception("No se pudo descargar la rúbrica.")

            with open(rubric_path, 'r', encoding='utf-8') as f:
                rubric_json = json.load(f)

            self.queue.put(("update_status", ("Obteniendo lista de entregas...",)))
            submissions = self.client.get_all_submissions(self.course_id, assignment_id)

            # --- FASE 1: Descargar PDFs y subirlos a la API de Gemini ---
            total_submissions = len(submissions)
            self.queue.put(("update_progress", 0))
            for i, sub in enumerate(submissions):
                progress = (i + 1) / total_submissions
                student_name = self._sanitize_filename(sub.get("user", {}).get("name", "sin_nombre"))
                self.queue.put(("update_status", (f"Preparando a {student_name} ({i+1}/{total_submissions})",)))
                self.queue.put(("update_progress", progress))

                all_attachments = []
                if "attachments" in sub: all_attachments.extend(sub["attachments"])
                if "submission_history" in sub:
                    for history_item in sub["submission_history"]:
                        if "attachments" in history_item: all_attachments.extend(history_item["attachments"])

                pdf_attachment = next((att for att in all_attachments if att.get("filename", "").lower().endswith(".pdf")), None)
                if not pdf_attachment:
                    logger.warning(f"Sin PDF para {student_name}, saltando.")
                    continue

                pdf_path = activity_path / student_name / self._sanitize_filename(pdf_attachment["filename"], decode_url=True)
                self.client.download_file(pdf_attachment["url"], pdf_path.parent, pdf_path.name)

                # Subir el archivo a Gemini y guardar su referencia
                gemini_file = self.gemini_evaluator._upload_file_to_gemini(str(pdf_path))
                uploaded_files[student_name] = gemini_file

            # --- FASE 2: Ejecutar las evaluaciones en paralelo ---
            self.queue.put(("update_status", ("Construyendo y enviando evaluaciones a la IA...",)))
            schema = "{'evaluacion': [{'criterio': str, 'puntuacion': float, 'justificacion': str}]}"

            if not uploaded_files:
                 raise Exception("No se encontraron entregas con PDF para evaluar.")

            self.queue.put(("show_progress_bar", {"indeterminate": True}))
            
            # Usaremos un ThreadPoolExecutor para enviar las peticiones concurrentemente.
            MAX_WORKERS = 8
            evaluations = []
            future_to_student = {}

            quota_exceeded = False
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                # Preparamos y enviamos todas las tareas al pool
                for student_name, gemini_file in uploaded_files.items():
                    contents = self.gemini_evaluator.prepare_pdf_evaluation_request(gemini_file.name, schema)
                    future = executor.submit(self.gemini_evaluator.execute_single_request, contents)
                    future_to_student[future] = student_name

                # --- FASE 3: Procesar resultados a medida que se completan ---
                self.queue.put(("update_status", ("Esperando y procesando respuestas de la IA...",)))
                self.queue.put(("show_progress_bar", {"indeterminate": False}))

                total_futures = len(future_to_student)
                for i, future in enumerate(concurrent.futures.as_completed(future_to_student)):
                    if quota_exceeded: # Si ya sabemos que la cuota se excedió, cancelamos el resto.
                        future.cancel()
                        continue

                    student_name = future_to_student[future]
                    progress = (i + 1) / total_futures
                    self.queue.put(("update_status", (f"Procesando resultado de {student_name} ({i+1}/{total_futures})",)))
                    self.queue.put(("update_progress", progress))
                    try:
                        # .result() obtiene el resultado de la tarea. Si hubo una excepción, la relanza.
                        result_json = future.result()
                        if "error" in result_json:
                            logger.error(f"Error en la respuesta para {student_name}: {result_json['error']}")
                            continue
                        result_json['alumno'] = student_name
                        evaluations.append(result_json)
                    except Exception as e:
                        error_str = str(e)
                        logger.error(f"Error en la evaluación de {student_name}: {error_str}", exc_info=False) # exc_info=False para no llenar el log con tracebacks de cuota
                        # ¡Detección inteligente del error de cuota!
                        if "429" in error_str and "quota" in error_str:
                            quota_exceeded = True
                            msg = ("Se ha excedido la cuota diaria de la API de Gemini (plan gratuito).\n\n"
                                   "El proceso se detendrá. Los resultados obtenidos hasta ahora se guardarán.\n"
                                   "Por favor, inténtalo de nuevo mañana o considera un plan de pago de Google.")
                            self.queue.put(("evaluation_error", msg))


            self.queue.put(("update_status", ("Guardando resultados...",)))
            self._save_evaluations_to_csv(evaluations, activity_path / "evaluaciones_gemini.csv")

            # --- Finalización Exitosa ---
            if not quota_exceeded:
                self.queue.put(("evaluation_success", len(evaluations)))

        except Exception as e:
            error_msg = f"Ocurrió un error durante la evaluación: {e}"
            logger.error(f"Error al evaluar entregas: {e}", exc_info=True)
            self.queue.put(("evaluation_error", error_msg))

        finally:
            # --- FASE 4: Limpieza de archivos subidos ---
            self.queue.put(("update_status", ("Limpiando archivos temporales de la API...",)))
            for student_name, gemini_file in uploaded_files.items():
                try:
                    logger.info(f"Eliminando archivo {gemini_file.name} de {student_name}...")
                    genai.delete_file(gemini_file.name)
                    logger.info(f"Archivo {gemini_file.name} de {student_name} eliminado correctamente.")
                except Exception as e:
                    logger.error(f"No se pudo eliminar el archivo {gemini_file.name}: {e}")
            self.queue.put(("evaluation_finished", None))

    def _on_evaluation_success(self, count):
        """Se llama cuando la evaluación en lote termina correctamente."""
        self.main_window.hide_progress_bar()
        self._enable_assignment_buttons(True)
        self.main_window.update_status("¡Evaluación completada!", clear_after_ms=5000)
        messagebox.showinfo(
            "Evaluación Completada",
            f"Se han evaluado {count} entregas con PDF.\nEl resultado se ha guardado en 'evaluaciones_gemini.csv'."
        )

    def _save_evaluations_to_csv(self, evaluations: list, csv_path: Path):
        """Guarda los resultados de la evaluación de Gemini en un archivo CSV."""
        if not evaluations:
            logger.warning("No se generaron evaluaciones para guardar en CSV.")
            return

        try:
            # Extraer todas las claves de los criterios del primer resultado para crear las cabeceras.
            # Esto asume que todos los resultados tienen los mismos criterios.
            first_result = evaluations[0]
            criteria_list = first_result.get('evaluacion', [])

            # Crear las cabeceras dinámicamente
            fieldnames = ['alumno']
            for crit in criteria_list:
                crit_name = crit.get('criterio', 'criterio_desconocido').strip()
                # Saneamos el nombre del criterio para que sea un nombre de columna válido
                sanitized_crit_name = re.sub(r'\s+', '_', crit_name.lower())
                sanitized_crit_name = re.sub(r'[^a-zA-Z0-9_]', '', sanitized_crit_name)
                fieldnames.append(f"{sanitized_crit_name}_puntuacion")
                fieldnames.append(f"{sanitized_crit_name}_justificacion")

            with csv_path.open('w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()

                for result in evaluations:
                    row = {'alumno': result.get('alumno', 'N/A')}
                    for crit_eval in result.get('evaluacion', []):
                        crit_name = crit_eval.get('criterio', 'criterio_desconocido').strip()
                        sanitized_crit_name = re.sub(r'\s+', '_', crit_name.lower())
                        sanitized_crit_name = re.sub(r'[^a-zA-Z0-9_]', '', sanitized_crit_name)
                        row[f"{sanitized_crit_name}_puntuacion"] = crit_eval.get('puntuacion')
                        row[f"{sanitized_crit_name}_justificacion"] = crit_eval.get('justificacion')
                    writer.writerow(row)

            logger.info(f"Resultados de la evaluación guardados en: {csv_path}")

        except Exception as e:
            logger.error(f"Error al guardar el archivo CSV de evaluaciones: {e}", exc_info=True)
            # Informar al usuario en el hilo principal
            self.after(0, messagebox.showerror, "Error de Escritura", f"No se pudo guardar el archivo CSV de resultados: {e}")

    def _build_evaluation_prompt(self, rubric_json: dict) -> str:
        """Construye el prompt para Gemini usando la rúbrica."""
        # Filtramos la rúbrica para enviar solo la información esencial al modelo,
        # evitando sobrecargarlo con IDs y metadatos innecesarios.
        criteria_data = []
        for crit in rubric_json.get('data', []):
            ratings_data = [
                {'description': r.get('description'), 'points': r.get('points')}
                for r in crit.get('ratings', [])
            ]
            criteria_data.append({
                'description': crit.get('description'),
                'points': crit.get('points'),
                'ratings': ratings_data
            })

        rubric_text = json.dumps(criteria_data, ensure_ascii=False, indent=2)
        return (
            "Eres un asistente de profesor universitario experto. Tu tarea es evaluar la entrega de un alumno (archivo PDF adjunto) "
            "utilizando la siguiente rúbrica de evaluación. Debes ser objetivo y basar tu puntuación y justificación "
            "únicamente en el contenido del documento y los criterios de la rúbrica.\n\n"
            "RÚBRICA (en formato JSON):\n"
            f"{rubric_text}\n\n"
            "INSTRUCCIONES DETALLADAS:\n"
            "1. **Analiza el PDF adjunto** en su totalidad para comprender el trabajo del alumno.\n"
            "2. **Evalúa cada criterio**: Para cada criterio de la rúbrica, elige el nivel de 'rating' que mejor se ajuste al contenido del PDF, asigna los 'points' correspondientes y escribe una 'justificacion' clara y concisa, haciendo referencia a partes específicas del documento si es posible.\n"
            "3. **Formato de Salida OBLIGATORIO**: Devuelve un ÚNICO objeto JSON válido y minificado. No incluyas explicaciones, comentarios, ni ```json ... ```. La respuesta debe ser exclusivamente el JSON.\n"
            "4. **Esquema del JSON**: El JSON debe tener una clave 'evaluacion' que contenga una lista de objetos. Cada objeto debe tener tres claves: 'criterio' (la descripción del criterio), 'puntuacion' (un número), y 'justificacion' (un string).\n"
            "5. **INSTRUCCIÓN CRÍTICA PARA CRITERIOS SIN EVIDENCIA**: Si en el documento no encuentras ninguna evidencia para poder evaluar un criterio específico, DEBES asignarle una puntuación de 0 y usar la siguiente justificación exacta: 'No se encontró evidencia en el documento para evaluar este criterio.'\n\n"
            "Ejemplo de la estructura de salida esperada: {'evaluacion': [{'criterio': 'Análisis del problema', 'puntuacion': 4.5, 'justificacion': 'El análisis es correcto y detallado, aunque podría mejorar la sección 2.1.'}]}"
        )

    def _create_abbreviation(self, text: str) -> str:
        """Crea una abreviatura a partir de un texto, usando las iniciales de las palabras significativas."""
        # Elimina contenido entre paréntesis o después de un guion, que suelen ser códigos.
        text_cleaned = re.sub(r'\(.*\)|-.*', '', text).strip()
        # Palabras a ignorar para no generar abreviaturas como "TAREADS" (Tarea de Sistemas)
        ignore_words = {'de', 'la', 'el', 'y', 'a', 'en', 'los', 'las', 'con', 'para', 'un', 'una', 'del'}

        # Tomamos la primera letra de cada palabra que no esté en la lista de ignoradas y no sea vacía.
        words = [word[0].upper() for word in text_cleaned.split() if word.lower() not in ignore_words and word]

        abbreviation = "".join(words)

        # Si la abreviatura está vacía (p.ej. "De la a"), usamos las 3 primeras letras del texto original saneado.
        if not abbreviation:
            return self._sanitize_filename(text_cleaned)[:3].upper()

        return abbreviation

    def _sanitize_filename(self, name, decode_url=False):
        """
        Sanea un nombre para que sea válido como parte de una ruta de archivo.
        Elimina caracteres ilegales. Opcionalmente, decodifica caracteres de URL.
        """
        if decode_url:
            # Decodifica caracteres como %20 (espacio) o %C3%B3 (ó)
            name = urllib.parse.unquote_plus(name)
        # Reemplaza caracteres no válidos para nombres de archivo/carpeta
        sanitized_name = re.sub(r'[\\/*?:"<>|]', "_", name)
        # Elimina espacios o puntos al principio o al final, que son problemáticos en Windows
        return sanitized_name.strip(" .")

    def _on_download_error(self, error_msg: str):
        """Función centralizada para manejar errores de descarga en la GUI."""
        self.main_window.hide_progress_bar()
        self.main_window.update_status("Error en la descarga.", clear_after_ms=8000)
        self._enable_assignment_buttons(True)
        messagebox.showerror("Error de Descarga", error_msg)

    def _handle_download_submissions(self, assignment_id, summary, base_dir):
        """Maneja la lógica de descarga en un hilo separado para no bloquear la UI."""
        try:
            assignment = self.assignments[assignment_id]
            course = self.client.get_course(self.course_id)
            
            # --- MEJORA: Usar abreviaturas para los nombres de las carpetas ---
            course_abbreviation = self._create_abbreviation(course.name)
            assignment_abbreviation = self._create_abbreviation(assignment['name'])
            course_folder_name = f"{self.course_id} - {course_abbreviation}"
            assignment_folder_name = f"{assignment_id} - {assignment_abbreviation}"

            # Usamos Path de pathlib para un manejo más robusto de las rutas
            base_path = Path(base_dir)
            activity_path = base_path / course_folder_name / assignment_folder_name
            
            self.after(0, self.main_window.update_status, "Obteniendo lista completa de entregas...")
            submissions = self.client.get_all_submissions(self.course_id, assignment_id)
            if not submissions:
                self.after(0, self.main_window.update_status, "No se encontraron entregas para esta actividad.", 5000)
                self.after(0, messagebox.showinfo, "Sin entregas", "No se encontraron entregas para esta actividad.")
                self.after(0, self.main_window.hide_progress_bar)
                self.after(0, self._enable_assignment_buttons, True)
                return

            downloaded_files = 0
            error_count = 0
            total_submissions = len(submissions)

            for i, sub in enumerate(submissions):
                progress = (i + 1) / total_submissions
                student_name = self._sanitize_filename(sub.get("user", {}).get("name", "sin_nombre"))
                self.after(0, self.main_window.update_status, f"Procesando {i+1}/{total_submissions}: {student_name}")
                self.after(0, self.main_window.update_progress, progress)

                attachments = []
                if "attachments" in sub:
                    attachments.extend(sub["attachments"])
                if "submission_history" in sub:
                    for history_item in sub["submission_history"]:
                        if "attachments" in history_item:
                            attachments.extend(history_item["attachments"])

                attachments = [dict(t) for t in {tuple(d.items()) for d in attachments}]

                if not attachments:
                    logger.warning(f"Sin adjuntos para {student_name} en la entrega {sub.get('id')}")
                    continue

                for att in attachments:
                    student_folder = activity_path / student_name
                    # --- MEJORA: Decodificar y sanear el nombre del archivo adjunto ---
                    filename = self._sanitize_filename(att["filename"], decode_url=True)
                    # Actualizamos el estado para mostrar el archivo actual, pero mantenemos la barra de progreso general
                    self.after(0, self.main_window.update_status, f"Descargando '{filename}' ({i+1}/{total_submissions})")
                    success = self.client.download_file(att["url"], student_folder, filename)
                    if success:
                        downloaded_files += 1
                    else:
                        error_count += 1

            if summary.get("has_rubric") and summary.get("rubric_id"):
                self.after(0, self.main_window.update_status, "Descargando rúbrica asociada...")
                # La rúbrica se guarda en la carpeta de la actividad
                rubric_base_name = f"rubrica_{assignment_folder_name}"
                self.client.export_rubric_to_json(self.course_id, summary["rubric_id"], activity_path / f"{rubric_base_name}.json")
                self.client.export_rubric_to_csv(self.course_id, summary["rubric_id"], activity_path / f"{rubric_base_name}.csv")

            # --- Finalización Exitosa ---
            def on_success():
                self.main_window.hide_progress_bar()
                self._enable_assignment_buttons(True)
                self.main_window.update_status("¡Descarga completada!", clear_after_ms=5000)
                final_message = f"Descarga completada.\n\nArchivos descargados: {downloaded_files}\nErrores: {error_count}"
                if summary.get("has_rubric"):
                    final_message += "\nLa rúbrica asociada ha sido guardada en formato JSON y CSV."
                messagebox.showinfo("Descarga Completada", final_message)
            
            self.after(0, on_success)

        except Exception as e:
            error_msg = f"Ocurrió un error durante la descarga: {e}"
            logger.error(f"Error al descargar entregas: {e}", exc_info=True)
            self.after(0, self._on_download_error, error_msg)

    @log_action
    def handle_create_activity(self):
        logger.info("Botón 'Crear Actividad' pulsado.")
        name = self.activity_name_entry.get()
        points = self.activity_points_entry.get()
        description = self.activity_desc_textbox.get("1.0", "end-1c")

        # Construir lista de submission_types desde el diccionario de checkboxes
        submission_types = [key for key, var in self.submission_checkboxes.items() if var.get() == "1"]

        if not submission_types:
            messagebox.showwarning("Campo Requerido", "Debes seleccionar al menos un tipo de entrega.")
            return

        if not name:
            messagebox.showwarning("Campo Requerido", "El nombre de la actividad no puede estar vacío.")
            return

        activity_settings = {
            'name': name,
            'submission_types': submission_types,
            'description': description,
            'published': False
        }
        try:
            if points:
                activity_settings['points_possible'] = int(points)
        except ValueError:
            messagebox.showwarning("Valor Inválido", "Los puntos deben ser un número.")
            return

        # NOTE: The user did not provide a `create_assignment` method.
        # I will assume it is a placeholder.
        messagebox.showinfo("En Desarrollo", "La creación de actividades aún no está implementada.")

        # success = self.client.create_assignment(self.course_id, activity_settings)
        # if success:
        #     messagebox.showinfo("Éxito", f"La actividad '{name}' ha sido creada correctamente.")
        #     # Limpiar campos
        #     self.activity_name_entry.delete(0, "end")
        #     self.activity_points_entry.delete(0, "end")
        #     self.activity_desc_textbox.delete("1.0", "end")
        #     for var in self.submission_checkboxes.values():
        #         var.set("0")