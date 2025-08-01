# app/gui/course_window.py

import customtkinter as ctk
from app.utils.logger_config import logger # Importar el logger

class CourseWindow(ctk.CTk):
    def __init__(self, courses: list):
        super().__init__()
        # ... (código del constructor sin cambios)
        self.title("Selección de Curso")
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
        self.selected_course_id = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        title_label = ctk.CTkLabel(self, text="Selecciona un curso para continuar", font=ctk.CTkFont(size=16, weight="bold"))
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        scrollable_frame = ctk.CTkScrollableFrame(self, label_text="Cursos Activos")
        scrollable_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        scrollable_frame.grid_columnconfigure(0, weight=1)
        if not courses:
            no_courses_label = ctk.CTkLabel(scrollable_frame, text="No se encontraron cursos activos.")
            no_courses_label.pack(pady=10)
        else:
            for i, course in enumerate(courses):
                button = ctk.CTkButton(
                    scrollable_frame,
                    text=course['name'],
                    command=lambda c=course: self.on_course_selected(c['id'], c['name']) # Pasamos también el nombre para el log
                )
                button.grid(row=i, column=0, padx=10, pady=(0, 8), sticky="ew")

    def on_course_selected(self, course_id: int, course_name: str):
        """Se llama cuando un usuario hace clic en un curso."""
        logger.info(f"Botón de curso pulsado. Selección: '{course_name}' (ID: {course_id})")
        self.selected_course_id = course_id
        self.destroy()

    def get_selected_course(self):
        self.mainloop()
        return self.selected_course_id