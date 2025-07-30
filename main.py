# main.py

import sys
import os
import customtkinter as ctk
from tkinter import messagebox

# Añade el directorio raíz del proyecto al 'path' de Python para encontrar el paquete 'app'
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from app.utils import config_manager
from app.api.canvas_client import CanvasClient
from app.gui.login_window import LoginWindow
from app.gui.course_window import CourseWindow
from app.gui.main_window import MainWindow


class App:
    def __init__(self):
        """
        Constructor principal de la aplicación que orquesta el flujo de inicio.
        """
        # Configuración de la apariencia visual de la aplicación
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # 1. Gestionar el login y obtener las credenciales
        credentials = self.handle_login()

        # Si el usuario no introduce credenciales, la aplicación termina.
        if not credentials:
            print("No se proporcionaron credenciales. Saliendo.")
            return

        # 2. Conectar a Canvas con las credenciales obtenidas
        client = CanvasClient(credentials['canvas_url'], credentials['api_token'])

        # Si hubo un error de conexión (ej. token inválido), mostrar error y salir.
        if client.error_message:
            messagebox.showerror("Error de Conexión", client.error_message)
            return

        # 3. Obtener la lista de cursos activos
        courses = client.get_active_courses()

        # Si hubo un error al obtener los cursos, mostrar error y salir.
        if courses is None:
            messagebox.showerror("Error", client.error_message or "No se pudieron obtener los cursos.")
            return

        # 4. Mostrar la ventana de selección de curso y esperar la elección del usuario
        course_win = CourseWindow(courses)
        selected_course_id = course_win.get_selected_course()

        # Si el usuario cierra la ventana sin elegir un curso, la aplicación termina.
        if not selected_course_id:
            print("No se seleccionó ningún curso. Saliendo.")
            return

        # 5. Abrir la ventana principal de la aplicación para el curso seleccionado
        main_app_window = MainWindow(client=client, course_id=selected_course_id)
        main_app_window.mainloop()

    def handle_login(self):
        """
        Gestiona la carga de credenciales existentes o solicita unas nuevas
        a través de la ventana de login.
        """
        credentials = config_manager.load_credentials()

        # Si no existen credenciales guardadas, mostrar la ventana de login
        if not credentials:
            login_win = LoginWindow()
            login_win.mainloop()  # La ejecución se pausa aquí hasta que se cierre la ventana

            # Intentar cargar de nuevo las credenciales por si se acaban de guardar
            credentials = config_manager.load_credentials()

        return credentials


if __name__ == "__main__":
    app = App()