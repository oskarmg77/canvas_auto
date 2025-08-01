# app/gui/main_window.py

import customtkinter as ctk
from app.api.canvas_client import CanvasClient
from tkinter import messagebox
from app.utils.logger_config import logger


class MainWindow(ctk.CTk):
    def __init__(self, client: CanvasClient, course_id: int):
        super().__init__()

        self.client = client
        self.course_id = course_id

        self.course = self.client.get_course(self.course_id)
        course_name = self.course.name if self.course else f"Curso ID: {self.course_id}"

        self.title(f"Canvas Auto - {course_name}")
        self.geometry("800x600")

        self.tab_view = ctk.CTkTabview(self, anchor="w")
        self.tab_view.pack(expand=True, fill="both", padx=10, pady=10)

        self.tab_view.add("Crear Quiz")
        self.tab_view.add("Ver Quizzes")
        self.tab_view.add("Crear Rúbrica")
        self.tab_view.add("Ver Rúbricas")
        self.tab_view.add("Crear Actividad")

        self.setup_quiz_tab()
        self.setup_view_quizzes_tab()
        self.setup_create_rubric_tab()
        self.setup_view_rubrics_tab()
        self.setup_activity_tab()

    def setup_quiz_tab(self):
        quiz_tab = self.tab_view.tab("Crear Quiz")
        quiz_tab.grid_columnconfigure(1, weight=1)
        title_label = ctk.CTkLabel(quiz_tab, text="Título del Quiz:")
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        self.quiz_title_entry = ctk.CTkEntry(quiz_tab, width=400)
        self.quiz_title_entry.grid(row=0, column=1, padx=20, pady=(20, 10), sticky="ew")
        type_label = ctk.CTkLabel(quiz_tab, text="Tipo de Quiz:")
        type_label.grid(row=1, column=0, padx=20, pady=10, sticky="w")
        self.quiz_type_combobox = ctk.CTkComboBox(quiz_tab, values=["Quiz Clásico", "Nuevo Quiz"])
        self.quiz_type_combobox.set("Quiz Clásico")
        self.quiz_type_combobox.grid(row=1, column=1, padx=20, pady=10, sticky="w")
        desc_label = ctk.CTkLabel(quiz_tab, text="Descripción / Instrucciones:")
        desc_label.grid(row=2, column=0, padx=20, pady=10, sticky="nw")
        self.quiz_desc_textbox = ctk.CTkTextbox(quiz_tab, height=200)
        self.quiz_desc_textbox.grid(row=2, column=1, padx=20, pady=10, sticky="nsew")
        quiz_tab.grid_rowconfigure(2, weight=1)
        create_button = ctk.CTkButton(quiz_tab, text="Crear Quiz", command=self.handle_create_quiz)
        create_button.grid(row=3, column=1, padx=20, pady=20, sticky="e")

    def handle_create_quiz(self):
        logger.info("Botón 'Crear Quiz' pulsado.")
        title = self.quiz_title_entry.get()
        description = self.quiz_desc_textbox.get("1.0", "end-1c")
        quiz_type_selection = self.quiz_type_combobox.get()
        if not title:
            messagebox.showwarning("Campo Requerido", "El título del quiz no puede estar vacío.")
            return
        settings = {'title': title, 'description': description, 'published': False}
        success = False
        if quiz_type_selection == "Nuevo Quiz":
            success = self.client.create_new_quiz(self.course_id, settings)
        else:
            settings['quiz_type'] = 'assignment'
            success = self.client.create_quiz(self.course_id, settings)
        if success:
            messagebox.showinfo("Éxito", f"El quiz '{title}' ha sido creado correctamente.")
            self.quiz_title_entry.delete(0, "end")
            self.quiz_desc_textbox.delete("1.0", "end")
        else:
            messagebox.showerror("Error", self.client.error_message or "Ocurrió un error al crear el quiz.")

    def setup_view_quizzes_tab(self):
        view_tab = self.tab_view.tab("Ver Quizzes")
        view_tab.grid_columnconfigure(0, weight=1)
        view_tab.grid_rowconfigure(1, weight=1)
        action_frame = ctk.CTkFrame(view_tab)
        action_frame.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        refresh_button = ctk.CTkButton(action_frame, text="Cargar Todos los Quizzes", command=self.handle_view_quizzes)
        refresh_button.pack(side="left")
        self.quiz_list_frame = ctk.CTkScrollableFrame(view_tab, label_text="Quizzes en el Curso")
        self.quiz_list_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

    def handle_view_quizzes(self):
        logger.info("Botón 'Cargar Todos los Quizzes' pulsado.")
        for widget in self.quiz_list_frame.winfo_children():
            widget.destroy()
        classic_quizzes = self.client.get_quizzes(self.course_id)
        new_quizzes = self.client.get_new_quizzes(self.course_id)
        if classic_quizzes is None or new_quizzes is None:
            messagebox.showerror("Error", self.client.error_message or "No se pudo cargar la lista de quizzes.")
            return
        all_quizzes = classic_quizzes + new_quizzes
        if not all_quizzes:
            label = ctk.CTkLabel(self.quiz_list_frame, text="No se encontraron quizzes en este curso.")
            label.pack(pady=10)
        else:
            if classic_quizzes:
                classic_header = ctk.CTkLabel(self.quiz_list_frame, text="Quizzes Clásicos",
                                              font=ctk.CTkFont(weight="bold"))
                classic_header.pack(anchor="w", padx=10, pady=(5, 2))
                for quiz in classic_quizzes:
                    label = ctk.CTkLabel(self.quiz_list_frame, text=f"• {quiz['title']} (ID: {quiz['id']})")
                    label.pack(anchor="w", padx=20, pady=2)
            if new_quizzes:
                new_header = ctk.CTkLabel(self.quiz_list_frame, text="Nuevos Quizzes", font=ctk.CTkFont(weight="bold"))
                new_header.pack(anchor="w", padx=10, pady=(15, 2))
                for quiz in new_quizzes:
                    label = ctk.CTkLabel(self.quiz_list_frame, text=f"• {quiz['title']} (ID: {quiz['id']})")
                    label.pack(anchor="w", padx=20, pady=2)

    def setup_create_rubric_tab(self):
        rubric_tab = self.tab_view.tab("Crear Rúbrica")
        rubric_tab.grid_columnconfigure(1, weight=1)
        title_label = ctk.CTkLabel(rubric_tab, text="Título de la Rúbrica:")
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        self.rubric_title_entry = ctk.CTkEntry(rubric_tab)
        self.rubric_title_entry.grid(row=0, column=1, padx=20, pady=(20, 10), sticky="ew")
        criteria_label = ctk.CTkLabel(rubric_tab, text="Criterios:")
        criteria_label.grid(row=1, column=0, padx=20, pady=10, sticky="nw")
        instructions_text = "Escribe cada criterio en una nueva línea con el formato:\n\ndescripción corta, descripción larga, puntos\n\nEjemplo:\nOrtografía, El texto no contiene errores ortográficos., 5"
        self.rubric_criteria_textbox = ctk.CTkTextbox(rubric_tab, height=200)
        self.rubric_criteria_textbox.insert("1.0", instructions_text)
        self.rubric_criteria_textbox.grid(row=1, column=1, padx=20, pady=10, sticky="nsew")
        rubric_tab.grid_rowconfigure(1, weight=1)
        create_button = ctk.CTkButton(rubric_tab, text="Crear Rúbrica", command=self.handle_create_rubric)
        create_button.grid(row=2, column=1, padx=20, pady=20, sticky="e")

    def handle_create_rubric(self):
        logger.info("Botón 'Crear Rúbrica' pulsado.")
        title = self.rubric_title_entry.get()
        criteria_text = self.rubric_criteria_textbox.get("1.0", "end-1c")
        if not title or not criteria_text or criteria_text.startswith("Escribe cada criterio"):
            messagebox.showwarning("Campos Requeridos", "El título y los criterios son obligatorios.")
            return
        success = self.client.create_rubric(self.course_id, title, criteria_text)
        if success:
            messagebox.showinfo("Éxito", f"La rúbrica '{title}' ha sido creada correctamente.")
            self.rubric_title_entry.delete(0, "end")
            self.rubric_criteria_textbox.delete("1.0", "end")
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
                label = ctk.CTkLabel(self.rubric_list_frame, text=f"• {rubric['title']} (ID: {rubric['id']})")
                label.pack(anchor="w", padx=10, pady=2)

    def setup_activity_tab(self):
        """Configura el contenido de la pestaña 'Crear Actividad'."""
        activity_tab = self.tab_view.tab("Crear Actividad")
        activity_tab.grid_columnconfigure(1, weight=1)
        name_label = ctk.CTkLabel(activity_tab, text="Nombre de la Actividad:")
        name_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        self.activity_name_entry = ctk.CTkEntry(activity_tab)
        self.activity_name_entry.grid(row=0, column=1, padx=20, pady=(20, 10), sticky="ew")
        points_label = ctk.CTkLabel(activity_tab, text="Puntos Posibles:")
        points_label.grid(row=1, column=0, padx=20, pady=10, sticky="w")
        self.activity_points_entry = ctk.CTkEntry(activity_tab)
        self.activity_points_entry.grid(row=1, column=1, padx=20, pady=10, sticky="w")
        submission_label = ctk.CTkLabel(activity_tab, text="Tipos de Entrega Online:")
        submission_label.grid(row=2, column=0, padx=20, pady=10, sticky="nw")
        submission_frame = ctk.CTkFrame(activity_tab)
        submission_frame.grid(row=2, column=1, padx=20, pady=10, sticky="w")
        self.sub_type_upload = ctk.CTkCheckBox(submission_frame, text="Subir archivo (online_upload)")
        self.sub_type_upload.pack(anchor="w", padx=10, pady=5)
        self.sub_type_text = ctk.CTkCheckBox(submission_frame, text="Entrada de texto (online_text_entry)")
        self.sub_type_text.pack(anchor="w", padx=10, pady=5)
        self.sub_type_url = ctk.CTkCheckBox(submission_frame, text="URL de un sitio web (online_url)")
        self.sub_type_url.pack(anchor="w", padx=10, pady=5)
        desc_label = ctk.CTkLabel(activity_tab, text="Descripción:")
        desc_label.grid(row=3, column=0, padx=20, pady=10, sticky="nw")
        self.activity_desc_textbox = ctk.CTkTextbox(activity_tab, height=150)
        self.activity_desc_textbox.grid(row=3, column=1, padx=20, pady=10, sticky="nsew")
        activity_tab.grid_rowconfigure(3, weight=1)
        create_button = ctk.CTkButton(activity_tab, text="Crear Actividad", command=self.handle_create_activity)
        create_button.grid(row=4, column=1, padx=20, pady=20, sticky="e")

    def handle_create_activity(self):
        """Gestiona la creación de una nueva actividad."""
        logger.info("Botón 'Crear Actividad' pulsado.")
        name = self.activity_name_entry.get()
        points = self.activity_points_entry.get()
        description = self.activity_desc_textbox.get("1.0", "end-1c")
        submission_types = []
        if self.sub_type_upload.get(): submission_types.append('online_upload')
        if self.sub_type_text.get(): submission_types.append('online_text_entry')
        if self.sub_type_url.get(): submission_types.append('online_url')
        if not submission_types:
            messagebox.showwarning("Campo Requerido", "Debes seleccionar al menos un tipo de entrega.")
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
        success = self.client.create_assignment(self.course_id, activity_settings)
        if success:
            messagebox.showinfo("Éxito", f"La actividad '{name}' ha sido creada correctamente.")
            self.activity_name_entry.delete(0, "end")
            self.activity_points_entry.delete(0, "end")
            self.activity_desc_textbox.delete("1.0", "end")
            self.sub_type_upload.deselect()
            self.sub_type_text.deselect()
            self.sub_type_url.deselect()
        else:
            messagebox.showerror("Error", self.client.error_message or "Ocurrió un error al crear la actividad.")