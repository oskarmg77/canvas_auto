# app/gui/course_window.py

import customtkinter as ctk


class CourseWindow(ctk.CTk):
    def __init__(self, courses: list):
        super().__init__()

        self.title("Selección de Curso")

        # --- CONSTANTES PARA EL TAMAÑO DE LA VENTANA ---
        BUTTON_HEIGHT_WITH_PADDING = 38  # Altura de cada botón + su espaciado vertical (pady)
        BASE_HEIGHT = 120  # Altura base para el título, márgenes, etc.
        MAX_HEIGHT = 600  # Altura máxima para que no ocupe toda la pantalla
        MIN_HEIGHT = 200  # Altura mínima si no hay cursos o son muy pocos

        # --- CÁLCULO DE LA ALTURA DINÁMICA ---
        num_courses = len(courses)
        if num_courses == 0:
            window_height = MIN_HEIGHT
        else:
            # Calculamos la altura necesaria en función del número de botones
            calculated_height = BASE_HEIGHT + (num_courses * BUTTON_HEIGHT_WITH_PADDING)
            # Nos aseguramos de que la altura no supere el máximo definido
            window_height = min(MAX_HEIGHT, calculated_height)

        # Aplicamos la geometría calculada
        self.geometry(f"500x{window_height}")

        self.selected_course_id = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        title_label = ctk.CTkLabel(self, text="Selecciona un curso para continuar",
                                   font=ctk.CTkFont(size=16, weight="bold"))
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Frame con scroll para la lista de cursos
        scrollable_frame = ctk.CTkScrollableFrame(self, label_text="Cursos Activos")
        scrollable_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        scrollable_frame.grid_columnconfigure(0, weight=1)

        if not courses:
            no_courses_label = ctk.CTkLabel(scrollable_frame, text="No se encontraron cursos activos.")
            no_courses_label.pack(pady=10)
        else:
            # Creamos un botón por cada curso
            for i, course in enumerate(courses):
                button = ctk.CTkButton(
                    scrollable_frame,
                    text=course['name'],
                    # Usamos lambda para pasar el id del curso al método
                    command=lambda c=course: self.on_course_selected(c['id'])
                )
                button.grid(row=i, column=0, padx=10, pady=(0, 8), sticky="ew")

    def on_course_selected(self, course_id: int):
        """Se llama cuando un usuario hace clic en un curso."""
        self.selected_course_id = course_id
        self.destroy()  # Cierra la ventana de selección

    def get_selected_course(self):
        """Permite que el código principal recupere el ID del curso."""
        self.mainloop()
        return self.selected_course_id