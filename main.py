# main.py

import sys
import os
import customtkinter as ctk
from tkinter import messagebox
from app.utils.logger_config import logger

# Añade el directorio raíz del proyecto al path de Python para encontrar el paquete 'app'
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from app.utils import config_manager
from app.api.canvas_client import CanvasClient
from app.api.gemini_client import HybridEvaluator
from app.gui.login_window import LoginWindow
from app.gui.course_window import CourseWindow
from app.gui.main_window import MainWindow


class App:
    def __init__(self):
        logger.info("Iniciando aplicación Canvas Auto...")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        credentials = self.handle_login()
        if not credentials:
            logger.warning("No se proporcionaron credenciales. Saliendo.")
            return

        self.client = CanvasClient(credentials['canvas_url'], credentials['api_token'])
        if self.client.error_message:
            messagebox.showerror("Error de Conexión", self.client.error_message)
            return

        # Extraer la clave de Gemini del mismo archivo de configuración
        gemini_api_key = credentials.get('gemini_api_key') if credentials else None

        # Crear una única instancia del cliente de Gemini
        try:
            self.gemini_evaluator = HybridEvaluator(api_key=gemini_api_key, logger=logger)
        except ImportError as e:
            logger.warning(f"No se pudo inicializar Gemini: {e}. La función de evaluación no estará disponible.")
            self.gemini_evaluator = None
        self.run_main_flow()

    def handle_login(self):
        """
        Gestiona la carga de credenciales existentes o solicita nuevas
        a través de la ventana de inicio de sesión.
        """
        credentials = config_manager.load_credentials()
        if not credentials:
            login_win = LoginWindow()
            login_win.mainloop()
            credentials = config_manager.load_credentials()
        return credentials

    def run_main_flow(self):
        """
        Ejecuta el flujo principal de la aplicación que puede ser reiniciado
        para seleccionar un nuevo curso.
        """
        while True:
            # Pasamos el cliente directamente a CourseWindow para que gestione la carga de cursos.
            course_win = CourseWindow(self.client)
            selected_course_id = course_win.get_selected_course()

            if not selected_course_id:
                logger.info("No se seleccionó ningún curso. Saliendo de la aplicación.")
                break  # El usuario cerró la ventana de selección

            main_app = MainWindow(client=self.client, course_id=selected_course_id, gemini_evaluator=self.gemini_evaluator)
            main_app.mainloop()

            # Si la ventana principal se cierra con el flag de reinicio, el bucle continuará.
            # De lo contrario, saldrá.
            if not main_app.restart:
                break

        logger.info("Aplicación cerrada.")


if __name__ == "__main__":
    app = App()