# app/gui/activities_menu.py

import customtkinter as ctk
from tkinter import messagebox, filedialog
from pathlib import Path
from app.utils.logger_config import logger
import os
import threading
import urllib.parse
import re

# Diccionario para los tipos de entrega. Clave: API, Valor: Texto en GUI
SUBMISSION_TYPES = {
    "online_upload": "Subir archivo",
    "online_text_entry": "Entrada de texto",
    "online_url": "URL de un sitio web",
}

class ActivitiesMenu(ctk.CTkFrame):
    def __init__(self, parent, client, course_id, back_callback):
        super().__init__(parent)
        self.client = client
        self.course_id = course_id
        self.back_callback = back_callback
        self.submission_checkboxes = {}  # Para almacenar las variables de los checkboxes
        self.assignments = {}
        self.assignment_buttons = {}
        self.selected_assignment_id = None
        self.active_thread = None  # Para controlar el hilo de descarga

        back_button = ctk.CTkButton(self, text="< Volver al Menú Principal", command=self.back_callback)
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

        # Frame para la lista de actividades
        self.assignments_frame = ctk.CTkScrollableFrame(download_tab, label_text="Actividades del Curso")
        self.assignments_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.assignments_frame.grid_columnconfigure(0, weight=1)

        # Etiqueta para mostrar el progreso de la descarga
        self.progress_label = ctk.CTkLabel(download_tab, text="", anchor="w")
        self.progress_label.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 10))

        self._load_assignments()

    def _load_assignments(self):
        for widget in self.assignments_frame.winfo_children():
            widget.destroy()
        self.assignments.clear()
        self.assignment_buttons.clear()
        self.selected_assignment_id = None
        self.selected_assignment_label.configure(text="Selecciona una actividad de la lista para ver detalles y descargar.")

        try:
            # Cambiamos a la nueva función que obtiene los grupos con sus actividades
            assignment_groups = self.client.get_assignment_groups_with_assignments(self.course_id)
            if not assignment_groups:
                messagebox.showinfo("Información", "No se encontraron grupos de actividades para este curso.")
                return

            # Iteramos sobre cada grupo de actividades
            for group in assignment_groups:
                # Creamos una etiqueta para el nombre del grupo
                group_label = ctk.CTkLabel(
                    self.assignments_frame,
                    text=group['name'],
                    font=ctk.CTkFont(size=14, weight="bold"),
                    anchor="w"
                )
                group_label.pack(fill="x", padx=5, pady=(10, 5))

                # Obtenemos las actividades de este grupo
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
                    # Guardamos la actividad en el diccionario plano para fácil acceso
                    self.assignments[assignment_id] = assignment
                    
                    # Creamos el botón para la actividad, con una sangría
                    btn = ctk.CTkButton(
                        self.assignments_frame,
                        text=assignment['name'],
                        command=lambda a_id=assignment_id: self._select_assignment(a_id)
                    )
                    # Usamos padx para crear la sangría visual
                    btn.pack(fill="x", padx=(20, 5), pady=2)
                    self.assignment_buttons[assignment_id] = btn

        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar las actividades: {e}")
            logger.error(f"Error al cargar actividades: {e}", exc_info=True)

    def _enable_assignment_buttons(self):
        """Helper para reactivar los botones de actividad en el hilo principal."""
        for btn in self.assignment_buttons.values():
            btn.configure(state="normal")

    def _select_assignment(self, assignment_id):
        """Se llama al pulsar un botón de actividad. Inicia la obtención de detalles."""
        if self.active_thread and self.active_thread.is_alive():
            messagebox.showwarning("Proceso en curso", "Espera a que termine el proceso actual.")
            return

        self.selected_assignment_id = assignment_id
        assignment_name = self.assignments[assignment_id]["name"]
        self.selected_assignment_label.configure(text=f"Actividad seleccionada: {assignment_name}")
        self.progress_label.configure(text="Obteniendo resumen de entregas...")
        logger.info(f"Actividad seleccionada: {assignment_name} (ID: {assignment_id}). Obteniendo resumen...")

        # Desactivar botones mientras se obtiene la información
        for btn in self.assignment_buttons.values():
            btn.configure(state="disabled")

        self.active_thread = threading.Thread(target=self._fetch_and_prompt_download, args=(assignment_id,))
        self.active_thread.start()

    def _fetch_and_prompt_download(self, assignment_id):
        """Obtiene el resumen y luego pregunta al usuario si desea descargar."""
        summary = self.client.get_assignment_submission_summary(self.course_id, assignment_id)

        # Reactivar botones en el hilo principal
        self.after(0, self._enable_assignment_buttons)

        if not summary:
            self.after(0, self.progress_label.configure, {"text": "Error al obtener resumen."})
            self.after(0, messagebox.showerror, "Error", self.client.error_message or "No se pudo obtener el resumen.")
            return

        def prompt_on_main_thread():
            assignment_name = self.assignments[assignment_id]["name"]
            info_message = (
                f"Actividad: {assignment_name}\n\n"
                f"• Total de entregas: {summary['submission_count']}\n"
                f"• Entregas con PDF: {summary['pdf_submission_count']}\n"
                f"• Tiene rúbrica asociada: {'Sí' if summary['has_rubric'] else 'No'}\n\n"
                "¿Deseas iniciar la descarga?"
            )
            self.progress_label.configure(text="Esperando confirmación del usuario...")

            if messagebox.askyesno("Confirmar Descarga", info_message):
                self._start_download_thread(assignment_id, summary)
            else:
                self.progress_label.configure(text="Descarga cancelada por el usuario.")
                self.selected_assignment_label.configure(text="Selecciona una actividad de la lista...")
                self.selected_assignment_id = None

        self.after(0, prompt_on_main_thread)

    def _start_download_thread(self, assignment_id, summary):
        """Inicia el proceso de descarga de archivos en un nuevo hilo."""
        base_dir = filedialog.askdirectory(title="Selecciona la carpeta base para las descargas")
        if not base_dir:
            self.progress_label.configure(text="Descarga cancelada.")
            return

        self.progress_label.configure(text="Iniciando descarga...")
        self.active_thread = threading.Thread(
            target=self._handle_download_submissions, args=(assignment_id, summary, base_dir)
        )
        self.active_thread.start()

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

    def _update_progress_label(self, text):
        """Planifica una actualización de la etiqueta de progreso en el hilo principal."""
        self.after(0, self.progress_label.configure, {"text": text})

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
            
            self._update_progress_label("Obteniendo lista completa de entregas...")
            submissions = self.client.get_all_submissions(self.course_id, assignment_id)
            if not submissions:
                self._update_progress_label("No se encontraron entregas para esta actividad.")
                self.after(0, messagebox.showinfo, "Sin entregas", "No se encontraron entregas para esta actividad.")
                return

            downloaded_files = 0
            error_count = 0
            total_submissions = len(submissions)

            for i, sub in enumerate(submissions):
                student_name = self._sanitize_filename(sub.get("user", {}).get("name", "sin_nombre"))
                self._update_progress_label(f"Procesando {i+1}/{total_submissions}: {student_name}")

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
                    self._update_progress_label(f"Descargando '{filename}' de {student_name}...")
                    success = self.client.download_file(att["url"], student_folder, filename)
                    if success:
                        downloaded_files += 1
                    else:
                        error_count += 1

            if summary.get("has_rubric") and summary.get("rubric_id"):
                self._update_progress_label("Descargando rúbrica asociada...")
                # La rúbrica se guarda en la carpeta de la actividad
                rubric_base_name = f"rubrica_{assignment_folder_name}"
                self.client.export_rubric_to_json(self.course_id, summary["rubric_id"], activity_path / f"{rubric_base_name}.json")
                self.client.export_rubric_to_csv(self.course_id, summary["rubric_id"], activity_path / f"{rubric_base_name}.csv")

            final_message = f"Descarga completada.\n\nArchivos descargados: {downloaded_files}\nErrores: {error_count}"
            if summary.get("has_rubric"):
                final_message += "\nLa rúbrica asociada ha sido guardada en formato JSON y CSV."
            self._update_progress_label("¡Descarga completada!")
            self.after(0, messagebox.showinfo, "Descarga Completada", final_message)

        except Exception as e:
            error_msg = f"Ocurrió un error durante la descarga: {e}"
            self._update_progress_label("Error en la descarga.")
            self.after(0, messagebox.showerror, "Error", error_msg)
            logger.error(f"Error al descargar entregas: {e}", exc_info=True)

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
        # else:
        #     messagebox.showerror("Error", self.client.error_message or "Ocurrió un error al crear la actividad.")