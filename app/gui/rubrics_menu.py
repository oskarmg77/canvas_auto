# app/gui/rubrics_menu.py

import customtkinter as ctk
from tkinter import messagebox, filedialog
import json
import csv
from app.utils.logger_config import logger


class RubricsMenu(ctk.CTkFrame):
    def __init__(self, parent, client, course_id, back_callback):
        super().__init__(parent)
        self.client = client
        self.course_id = course_id
        self.back_callback = back_callback
        self.imported_criteria = None

        back_button = ctk.CTkButton(self, text="< Volver al Menú Principal", command=self.back_callback)
        back_button.pack(anchor="nw", padx=10, pady=10)

        self.tab_view = ctk.CTkTabview(self, anchor="w")
        self.tab_view.pack(expand=True, fill="both", padx=10, pady=(0, 10))

        self.tab_view.add("Crear Rúbrica")
        self.tab_view.add("Ver Rúbricas")

        self.setup_create_rubric_tab()
        self.setup_view_rubrics_tab()

    def setup_create_rubric_tab(self):
        rubric_tab = self.tab_view.tab("Crear Rúbrica")
        rubric_tab.grid_columnconfigure(1, weight=3)
        rubric_tab.grid_columnconfigure(2, weight=1)
        rubric_tab.grid_rowconfigure(2, weight=1)

        title_label = ctk.CTkLabel(rubric_tab, text="Título de la Rúbrica:")
        title_label.grid(row=0, column=1, padx=20, pady=(20, 5), sticky="w")
        self.rubric_title_entry = ctk.CTkEntry(rubric_tab)
        self.rubric_title_entry.grid(row=0, column=2, padx=20, pady=(20, 5), sticky="ew")

        criteria_label = ctk.CTkLabel(rubric_tab, text="Criterios (para creación manual o importación simple):")
        criteria_label.grid(row=1, column=1, padx=20, pady=(10, 5), sticky="w")
        self.instructions_text = "Escribe cada criterio en una nueva línea con el formato:\n\ndescripción corta, descripción larga, puntos\n\nEjemplo:\nOrtografía, El texto no contiene errores ortográficos., 5"
        self.rubric_criteria_textbox = ctk.CTkTextbox(rubric_tab)
        self.rubric_criteria_textbox.insert("1.0", self.instructions_text)
        self.rubric_criteria_textbox.grid(row=2, column=1, padx=20, pady=(0, 10), sticky="nsew")

        options_frame = ctk.CTkFrame(rubric_tab)
        options_frame.grid(row=1, column=2, rowspan=2, padx=20, pady=(10, 10), sticky="ns")
        options_label = ctk.CTkLabel(options_frame, text="Opciones", font=ctk.CTkFont(weight="bold"))
        options_label.pack(padx=10, pady=(10, 5), anchor="w")
        self.free_form_comments_check = ctk.CTkCheckBox(options_frame, text="Permitir comentarios libres")
        self.free_form_comments_check.pack(padx=10, pady=10, anchor="w")
        self.free_form_comments_check.select()
        self.hide_score_check = ctk.CTkCheckBox(options_frame, text="Ocultar puntuación total")
        self.hide_score_check.pack(padx=10, pady=10, anchor="w")
        purpose_label = ctk.CTkLabel(options_frame, text="Propósito:")
        purpose_label.pack(padx=10, pady=(10, 0), anchor="w")
        self.purpose_combo = ctk.CTkComboBox(options_frame, values=["grading", "bookmark"])
        self.purpose_combo.set("grading")
        self.purpose_combo.pack(padx=10, pady=5, anchor="w")

        action_frame = ctk.CTkFrame(rubric_tab)
        action_frame.grid(row=3, column=1, columnspan=2, padx=20, pady=20, sticky="e")
        import_button = ctk.CTkButton(action_frame, text="Importar Rúbrica", command=self.handle_import_rubric)
        import_button.pack(side="left", padx=(0, 10))
        create_button = ctk.CTkButton(action_frame, text="Crear Rúbrica", command=self.handle_create_rubric)
        create_button.pack(side="left")

    def handle_import_rubric(self):
        logger.info("Botón 'Importar Rúbrica' pulsado.")
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo de rúbrica",
            filetypes=[("Archivos de Rúbrica", "*.csv *.json"), ("Todos los archivos", "*.*")]
        )
        if not file_path:
            logger.warning("Importación cancelada por el usuario.")
            return
        try:
            self.imported_criteria = None
            if file_path.lower().endswith('.json'):
                self.import_from_json(file_path)
            elif file_path.lower().endswith('.csv'):
                self.import_from_csv(file_path)
            else:
                messagebox.showerror("Formato no Soportado", "Por favor, selecciona un archivo .csv o .json.")
                return
            messagebox.showinfo("Importación Exitosa",
                                "Los datos de la rúbrica se han cargado. Revisa el formulario y pulsa 'Crear Rúbrica'.")
        except Exception as e:
            logger.error(f"Error al importar el archivo {file_path}: {e}", exc_info=True)
            messagebox.showerror("Error de Importación",
                                 f"No se pudo procesar el archivo.\nAsegúrate de que el formato es correcto.\n\nError: {e}")
            self.imported_criteria = None

    def import_from_json(self, file_path):
        """
        Carga datos desde un archivo JSON, manejando correctamente tanto
        listas como diccionarios de criterios.
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        rubric_data = data.get('rubric', data)
        association_data = data.get('rubric_association', {})

        self.rubric_title_entry.delete(0, 'end')
        self.rubric_title_entry.insert(0, rubric_data.get('title', ''))

        # --- LÓGICA CORREGIDA ---
        # Obtenemos el objeto de criterios
        criteria_object = rubric_data.get('criteria', {})

        # Comprobamos si es un diccionario (como en tu archivo) o una lista
        if isinstance(criteria_object, dict):
            # Si es un diccionario, nos quedamos con sus valores
            self.imported_criteria = list(criteria_object.values())
        elif isinstance(criteria_object, list):
            # Si ya es una lista, la usamos directamente
            self.imported_criteria = criteria_object
        else:
            # Si no es ninguno, es un formato inválido
            self.imported_criteria = []

        # El resto de la función sigue igual
        criteria_preview = []
        for crit in self.imported_criteria:
            desc = crit.get('description', '')
            points = crit.get('points', 0)
            ratings_count = len(crit.get('ratings', []))
            preview_text = f"{desc} ({ratings_count} niveles, {points} pts max)"
            criteria_preview.append(preview_text)

        self.rubric_criteria_textbox.delete("1.0", "end")
        if criteria_preview:
            self.rubric_criteria_textbox.insert("1.0", "RÚBRICA COMPLEJA IMPORTADA:\n" + "\n".join(criteria_preview))
        else:
            self.rubric_criteria_textbox.insert("1.0", "Error: El JSON no contenía criterios válidos.")

        if rubric_data.get('free_form_criterion_comments'):
            self.free_form_comments_check.select()
        else:
            self.free_form_comments_check.deselect()
        if association_data.get('hide_score_total', False):
            self.hide_score_check.select()
        else:
            self.hide_score_check.deselect()
        self.purpose_combo.set(association_data.get('purpose', 'grading'))

    def import_from_csv(self, file_path):
        criteria_text = []
        with open(file_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) < 3: continue
                criteria_text.append(",".join(row))
        self.rubric_criteria_textbox.delete("1.0", "end")
        self.rubric_criteria_textbox.insert("1.0", "\n".join(criteria_text))
        self.rubric_title_entry.delete(0, 'end')
        self.rubric_title_entry.insert(0, "Rúbrica desde CSV (editar título)")

    def handle_create_rubric(self):
        logger.info("Botón 'Crear Rúbrica' pulsado.")
        title = self.rubric_title_entry.get()
        rubric_options = {
            'free_form_criterion_comments': bool(self.free_form_comments_check.get()),
            'hide_score_total': bool(self.hide_score_check.get()),
            'purpose': self.purpose_combo.get()
        }
        criteria_to_send = []
        if self.imported_criteria:
            criteria_to_send = self.imported_criteria
            logger.info("Usando criterios estructurados importados desde JSON.")
        else:
            logger.info("Procesando criterios desde el cuadro de texto.")
            criteria_text = self.rubric_criteria_textbox.get("1.0", "end-1c").strip()
            if not title or not criteria_text or criteria_text == self.instructions_text.strip():
                messagebox.showwarning("Campos Requeridos", "El título y los criterios son obligatorios.")
                return

            lines = criteria_text.strip().split('\n')
            for i, line in enumerate(lines):
                if not line.strip(): continue

                # --- LÓGICA DE PARSEO ROBUSTA (LA CORRECCIÓN ESTÁ AQUÍ) ---
                first_comma = line.find(',')
                last_comma = line.rfind(',')
                if first_comma == -1 or last_comma == -1 or first_comma == last_comma:
                    messagebox.showerror("Error de Formato",
                                         f"La línea {i + 1} no tiene el formato correcto (desc_corta,desc_larga,puntos).")
                    return

                desc = line[:first_comma].strip()
                long_desc = line[first_comma + 1:last_comma].strip()
                points_str = line[last_comma + 1:].strip()

                if not points_str.isdigit():
                    messagebox.showerror("Error de Formato",
                                         f"Los puntos '{points_str}' en la línea {i + 1} no son un número válido.")
                    return

                criteria_to_send.append({
                    'description': desc,
                    'long_description': long_desc,
                    'points': int(points_str)
                })

        success = self.client.create_rubric(self.course_id, title, criteria_to_send, rubric_options)

        if success:
            messagebox.showinfo("Éxito", f"La rúbrica '{title}' ha sido creada correctamente.")
            self.rubric_title_entry.delete(0, "end")
            self.rubric_criteria_textbox.delete("1.0", "end")
            self.rubric_criteria_textbox.insert("1.0", self.instructions_text)
            self.imported_criteria = None
        else:
            messagebox.showerror("Error", self.client.error_message or "Ocurrió un error al crear la rúbrica.")

    def setup_view_rubrics_tab(self):
        view_tab = self.tab_view.tab("Ver Rúbricas")
        view_tab.grid_columnconfigure(0, weight=1)
        view_tab.grid_rowconfigure(1, weight=1)
        action_frame = ctk.CTkFrame(view_tab)
        action_frame.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        refresh_button = ctk.CTkButton(action_frame, text="Cargar Rúbricas", command=self.handle_view_rubrics)
        refresh_button.pack(side="left")
        self.rubric_list_frame = ctk.CTkScrollableFrame(view_tab, label_text="Rúbricas en el Curso")
        self.rubric_list_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

    def handle_view_rubrics(self):
        logger.info("Botón 'Cargar Rúbricas' pulsado.")
        for widget in self.rubric_list_frame.winfo_children():
            widget.destroy()
        rubrics = self.client.get_rubrics(self.course_id)
        if rubrics is None:
            messagebox.showerror("Error", self.client.error_message or "No se pudo cargar la lista de rúbricas.")
            return
        if not rubrics:
            label = ctk.CTkLabel(self.rubric_list_frame, text="No se encontraron rúbricas en este curso.")
            label.pack(pady=10)
        else:
            for rubric in rubrics:
                details = f"• {rubric['title']} (ID: {rubric['id']}) - Puntos: {rubric.get('points_possible', 'N/A')}"
                label = ctk.CTkLabel(self.rubric_list_frame, text=details)
                label.pack(anchor="w", padx=10, pady=2)