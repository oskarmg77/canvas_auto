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
        self.tab_view.add("Ver Quizzes")
        self.tab_view.add("Crear Rúbrica")
        self.tab_view.add("Crear Actividad")

        self.setup_quiz_tab()
        self.setup_view_quizzes_tab()
        self.setup_rubric_tab()
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
        """Obtiene y muestra la lista de todos los quizzes (clásicos y nuevos)."""
        for widget in self.quiz_list_frame.winfo_children():
            widget.destroy()

        # Obtener ambas listas de quizzes
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
            # Mostrar quizzes clásicos
            if classic_quizzes:
                classic_header = ctk.CTkLabel(self.quiz_list_frame, text="Quizzes Clásicos",
                                              font=ctk.CTkFont(weight="bold"))
                classic_header.pack(anchor="w", padx=10, pady=(5, 2))
                for quiz in classic_quizzes:
                    label = ctk.CTkLabel(self.quiz_list_frame, text=f"• {quiz['title']} (ID: {quiz['id']})")
                    label.pack(anchor="w", padx=20, pady=2)

            # Mostrar nuevos quizzes
            if new_quizzes:
                new_header = ctk.CTkLabel(self.quiz_list_frame, text="Nuevos Quizzes", font=ctk.CTkFont(weight="bold"))
                new_header.pack(anchor="w", padx=10, pady=(15, 2))
                for quiz in new_quizzes:
                    label = ctk.CTkLabel(self.quiz_list_frame, text=f"• {quiz['title']} (ID: {quiz['id']})")
                    label.pack(anchor="w", padx=20, pady=2)

    def setup_rubric_tab(self):
        rubric_tab = self.tab_view.tab("Crear Rúbrica")
        label = ctk.CTkLabel(rubric_tab, text="Aquí irán las herramientas para crear una Rúbrica.",
                             font=ctk.CTkFont(size=14))
        label.pack(padx=20, pady=20)

    def setup_activity_tab(self):
        activity_tab = self.tab_view.tab("Crear Actividad")
        label = ctk.CTkLabel(activity_tab, text="Aquí irán las herramientas para crear una Actividad.",
                             font=ctk.CTkFont(size=14))
        label.pack(padx=20, pady=20)