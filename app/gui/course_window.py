# app/gui/course_window.py

import customtkinter as ctk
import threading
from tkinter import messagebox
from app.utils.logger_config import logger # Importar el logger

class CourseWindow(ctk.CTk):
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.selected_course_id = None

        self.title("Selección de Curso")
        # Geometría inicial mientras se cargan los cursos
        self.geometry("500x250")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        title_label = ctk.CTkLabel(self, text="Selecciona un curso para continuar", font=ctk.CTkFont(size=16, weight="bold"))
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.scrollable_frame = ctk.CTkScrollableFrame(self, label_text="Cursos Activos")
        self.scrollable_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.scrollable_frame.grid_columnconfigure(0, weight=1)

        # Mensaje de carga inicial
        self.loading_label = ctk.CTkLabel(self.scrollable_frame, text="Cargando cursos, por favor espera...")
        self.loading_label.pack(pady=20)

        # Iniciar la carga en un hilo para no bloquear la GUI
        threading.Thread(target=self._load_courses, daemon=True).start()

    def _load_courses(self):
        """Carga los cursos en un hilo secundario y actualiza la GUI."""
        logger.info("Iniciando la carga de cursos en segundo plano...")
        courses = self.client.get_active_courses()
        # Planifica la actualización de la GUI en el hilo principal
        self.after(0, self._populate_courses_list, courses)

    def _populate_courses_list(self, courses):
        """Puebla la lista de cursos en el hilo principal."""
        self.loading_label.destroy() # Elimina el mensaje de "cargando"

        if courses is None:
            # Si hubo un error en la API, muestra el mensaje y cierra.
            messagebox.showerror("Error", self.client.error_message or "No se pudo obtener la lista de cursos.")
            self.destroy()
            return

        # --- Recalcular la altura de la ventana dinámicamente ---
        BUTTON_HEIGHT_WITH_PADDING = 38
        BASE_HEIGHT = 120
        MAX_HEIGHT = 600
        MIN_HEIGHT = 200
        num_courses = len(courses)

        if num_courses == 0:
            window_height = MIN_HEIGHT
        else:
            calculated_height = BASE_HEIGHT + (num_courses * BUTTON_HEIGHT_WITH_PADDING)
            window_height = min(MAX_HEIGHT, calculated_height)
        self.geometry(f"500x{window_height}")

        # --- Poblar la lista de cursos ---
        if not courses:
            no_courses_label = ctk.CTkLabel(self.scrollable_frame, text="No se encontraron cursos activos.")
            no_courses_label.pack(pady=10)
        else:
            for i, course in enumerate(courses):
                button = ctk.CTkButton(
                    self.scrollable_frame,
                    text=course['name'],
                    command=lambda c=course: self.on_course_selected(c['id'], c['name']) # Pasamos también el nombre para el log
                )
                button.grid(row=i, column=0, padx=10, pady=(0, 8), sticky="ew")

    def on_course_selected(self, course_id: int, course_name: str):
        logger.info(f"Botón de curso pulsado. Selección: '{course_name}' (ID: {course_id})")
        self.selected_course_id = course_id
        self.destroy()

    def get_selected_course(self):
        self.mainloop()
        return self.selected_course_id