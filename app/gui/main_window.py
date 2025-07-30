# app/gui/main_window.py

import customtkinter as ctk
from app.api.canvas_client import CanvasClient
from tkinter import messagebox


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
        self.tab_view.add("Crear Rúbrica")
        self.tab_view.add("Crear Actividad")

        self.setup_quiz_tab()
        self.setup_rubric_tab()
        self.setup_activity_tab()

    def setup_quiz_tab(self):
        """Configura el contenido de la pestaña 'Crear Quiz' con widgets reales."""
        quiz_tab = self.tab_view.tab("Crear Quiz")
        quiz_tab.grid_columnconfigure(1, weight=1)

        # Campo para el Título del Quiz
        title_label = ctk.CTkLabel(quiz_tab, text="Título del Quiz:")
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        self.quiz_title_entry = ctk.CTkEntry(quiz_tab, width=400)
        self.quiz_title_entry.grid(row=0, column=1, padx=20, pady=(20, 10), sticky="ew")

        # --- ¡NUEVO WIDGET! ---
        # Menú para seleccionar el tipo de Quiz
        type_label = ctk.CTkLabel(quiz_tab, text="Tipo de Quiz:")
        type_label.grid(row=1, column=0, padx=20, pady=10, sticky="w")
        self.quiz_type_combobox = ctk.CTkComboBox(
            quiz_tab,
            values=["Quiz Clásico", "Nuevo Quiz"]
        )
        self.quiz_type_combobox.set("Quiz Clásico")  # Valor por defecto
        self.quiz_type_combobox.grid(row=1, column=1, padx=20, pady=10, sticky="w")

        # Campo para la Descripción
        desc_label = ctk.CTkLabel(quiz_tab, text="Descripción / Instrucciones:")
        desc_label.grid(row=2, column=0, padx=20, pady=10, sticky="nw")
        self.quiz_desc_textbox = ctk.CTkTextbox(quiz_tab, height=200)
        self.quiz_desc_textbox.grid(row=2, column=1, padx=20, pady=10, sticky="nsew")
        quiz_tab.grid_rowconfigure(2, weight=1)

        # Botón para crear el Quiz
        create_button = ctk.CTkButton(quiz_tab, text="Crear Quiz", command=self.handle_create_quiz)
        create_button.grid(row=3, column=1, padx=20, pady=20, sticky="e")

    def handle_create_quiz(self):
        """Lógica que se ejecuta al pulsar el botón 'Crear Quiz'."""
        title = self.quiz_title_entry.get()
        description = self.quiz_desc_textbox.get("1.0", "end-1c")
        quiz_type_selection = self.quiz_type_combobox.get()

        if not title:
            messagebox.showwarning("Campo Requerido", "El título del quiz no puede estar vacío.")
            return

        quiz_settings = {
            'title': title,
            'description': description,
            'quiz_type': 'assignment',
            'published': False
        }

        # --- LÓGICA ACTUALIZADA ---
        # Añadimos el parámetro 'engine' si se selecciona "Nuevo Quiz"
        if quiz_type_selection == "Nuevo Quiz":
            quiz_settings['engine'] = 'quizzes.next'

        success = self.client.create_quiz(self.course_id, quiz_settings)

        if success:
            messagebox.showinfo("Éxito", f"El quiz '{title}' ha sido creado correctamente.")
            self.quiz_title_entry.delete(0, "end")
            self.quiz_desc_textbox.delete("1.0", "end")
        else:
            messagebox.showerror("Error", self.client.error_message or "Ocurrió un error al crear el quiz.")

    def setup_rubric_tab(self):
        """Configura el contenido de la pestaña 'Crear Rúbrica'."""
        rubric_tab = self.tab_view.tab("Crear Rúbrica")
        label = ctk.CTkLabel(rubric_tab, text="Aquí irán las herramientas para crear una Rúbrica.",
                             font=ctk.CTkFont(size=14))
        label.pack(padx=20, pady=20)

    def setup_activity_tab(self):
        """Configura el contenido de la pestaña 'Crear Actividad'."""
        activity_tab = self.tab_view.tab("Crear Actividad")
        label = ctk.CTkLabel(activity_tab, text="Aquí irán las herramientas para crear una Actividad.",
                             font=ctk.CTkFont(size=14))
        label.pack(padx=20, pady=20)