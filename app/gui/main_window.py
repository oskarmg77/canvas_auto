# app/gui/main_window.py

import customtkinter as ctk
from app.api.canvas_client import CanvasClient
from .quizzes_menu import QuizzesMenu
from .rubrics_menu import RubricsMenu
from .activities_menu import ActivitiesMenu
from app.utils.logger_config import logger

# Importaciones necesarias para manejar imágenes
import os
from PIL import Image


class MainWindow(ctk.CTk):
    def __init__(self, client: CanvasClient, course_id: int):
        super().__init__()

        self.client = client
        self.course_id = course_id
        self.restart = False

        # --- CONFIGURACIÓN DE LA VENTANA PRINCIPAL ---
        course = self.client.get_course(self.course_id)
        self.course_name = course.name if course else f"Curso ID: {self.course_id}"
        self.title(f"Canvas Auto - {self.course_name}")
        self.geometry("800x600")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- CARGAR ICONOS (con mayor tamaño) ---
        self.load_icons()

        # --- SUBMENÚS (INICIALMENTE OCULTOS) ---
        self.quizzes_frame = QuizzesMenu(self, self.client, self.course_id, self.show_main_menu)
        self.rubrics_frame = RubricsMenu(self, self.client, self.course_id, self.show_main_menu)
        self.activities_frame = ActivitiesMenu(self, self.client, self.course_id, self.show_main_menu)

        # --- INICIAR EL MENÚ PRINCIPAL ---
        self.setup_main_menu()

    def load_icons(self):
        """Carga las imágenes para los botones del menú con un tamaño mayor."""
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icons")

        # Aumentamos el tamaño de los iconos a 100x100 píxeles
        self.quiz_icon = self.get_ctk_image(os.path.join(icon_path, "quiz_icon.png"), size=(100, 100))
        self.rubric_icon = self.get_ctk_image(os.path.join(icon_path, "rubric_icon.png"), size=(100, 100))
        self.activity_icon = self.get_ctk_image(os.path.join(icon_path, "activity_icon.png"), size=(100, 100))
        self.course_icon = self.get_ctk_image(os.path.join(icon_path, "course_icon.png"), size=(100, 100))

    def get_ctk_image(self, path, size=(64, 64)):
        """Carga una imagen y la convierte a CTkImage, manejando errores."""
        try:
            return ctk.CTkImage(light_image=Image.open(path),
                                dark_image=Image.open(path),
                                size=size)
        except FileNotFoundError:
            logger.error(f"No se pudo encontrar el icono en la ruta: {path}")
            return ctk.CTkImage(light_image=Image.new('RGB', size, 'grey'), size=size)

    def create_card_button(self, parent, icon_image, text, command):
        """Crea una tarjeta interactiva que ocupa el espacio disponible."""

        # La tarjeta principal, con radio de esquina y cursor de mano.
        # Se inicializa sin borde visible (border_width=0).
        card = ctk.CTkFrame(parent, corner_radius=15, cursor="hand2", border_width=0)

        # --- FUNCIONES DE HOVER ---
        def on_enter(event):
            # Al entrar, se crea un borde de 2px con un color específico.
            card.configure(border_color="#1F6AA5", border_width=2)

        def on_leave(event):
            # Al salir, el borde simplemente se vuelve de grosor 0, haciéndolo invisible.
            # Ya NO se menciona el border_color.
            card.configure(border_width=0)

        # --- BINDINGS (EVENTOS) ---
        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

        # Centrar el contenido dentro de la tarjeta
        card.grid_rowconfigure(0, weight=1)  # Espacio vacío arriba
        card.grid_rowconfigure(1, weight=0)  # Icono
        card.grid_rowconfigure(2, weight=0)  # Texto
        card.grid_rowconfigure(3, weight=1)  # Espacio vacío abajo
        card.grid_columnconfigure(0, weight=1)  # Columna central

        # Etiqueta para el icono
        icon_label = ctk.CTkLabel(card, image=icon_image, text="")
        icon_label.grid(row=1, column=0, pady=(0, 10))

        # Etiqueta para el texto (más grande y en negrita)
        text_label = ctk.CTkLabel(card, text=text, font=ctk.CTkFont(size=18, weight="bold"))
        text_label.grid(row=2, column=0, padx=10, pady=(0, 15))

        # --- Función de clic ---
        def on_click(event):
            command()

        # Vincular el evento de clic a todos los elementos de la tarjeta
        card.bind("<Button-1>", on_click)
        icon_label.bind("<Button-1>", on_click)
        text_label.bind("<Button-1>", on_click)

        return card

    def setup_main_menu(self):
        """Crea la parrilla de tarjetas que se expanden para llenar la ventana."""
        self.main_menu_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_menu_frame.grid(row=0, column=0, sticky="nsew")

        # Configurar la parrilla para que las filas y columnas se expandan
        self.main_menu_frame.grid_rowconfigure(0, weight=0)  # Fila para el título (no se expande)
        self.main_menu_frame.grid_rowconfigure((1, 2), weight=1)  # Filas para las tarjetas (se expanden)
        self.main_menu_frame.grid_columnconfigure((0, 1), weight=1)  # Columnas (se expanden)

        # Título del curso (más grande)
        title_label = ctk.CTkLabel(self.main_menu_frame, text=self.course_name,
                                   font=ctk.CTkFont(size=28, weight="bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(40, 30))

        # --- Crear las tarjetas ---
        # sticky="nsew" hace que la tarjeta llene completamente su celda en la parrilla.
        # padx/pady añade un espacio entre las tarjetas.
        quiz_card = self.create_card_button(self.main_menu_frame, self.quiz_icon, "Quizzes", self.show_quizzes_menu)
        quiz_card.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")

        rubric_card = self.create_card_button(self.main_menu_frame, self.rubric_icon, "Rúbricas",
                                              self.show_rubrics_menu)
        rubric_card.grid(row=1, column=1, padx=20, pady=20, sticky="nsew")

        activity_card = self.create_card_button(self.main_menu_frame, self.activity_icon, "Actividades",
                                                self.show_activities_menu)
        activity_card.grid(row=2, column=0, padx=20, pady=20, sticky="nsew")

        course_card = self.create_card_button(self.main_menu_frame, self.course_icon, "Cambiar Curso",
                                              self.change_course)
        course_card.grid(row=2, column=1, padx=20, pady=20, sticky="nsew")

    def show_frame(self, frame_to_show):
        self.main_menu_frame.grid_forget()
        frame_to_show.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def show_main_menu(self):
        self.quizzes_frame.grid_forget()
        self.rubrics_frame.grid_forget()
        self.activities_frame.grid_forget()
        self.main_menu_frame.grid(row=0, column=0, sticky="nsew")

    def show_quizzes_menu(self):
        logger.info("Navegando al menú de quizzes.")
        self.show_frame(self.quizzes_frame)

    def show_rubrics_menu(self):
        logger.info("Navegando al menú de rúbricas.")
        self.show_frame(self.rubrics_frame)

    def show_activities_menu(self):
        logger.info("Navegando al menú de actividades.")
        self.show_frame(self.activities_frame)

    def change_course(self):
        logger.info("Botón 'Seleccionar otro Curso' pulsado. Reiniciando flujo.")
        self.restart = True
        self.destroy()