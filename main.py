# main.py

import sys
import os
import customtkinter as ctk
from tkinter import messagebox

# Adds the project root directory to Python's path to find the 'app' package
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
        Main application constructor that orchestrates the startup flow.
        """
        # Set the visual appearance for the application
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # 1. Handle login and get credentials
        credentials = self.handle_login()

        # If the user doesn't provide credentials, the application exits.
        if not credentials:
            print("No credentials provided. Exiting.")
            return

        # 2. Connect to Canvas with the obtained credentials
        client = CanvasClient(credentials['canvas_url'], credentials['api_token'])

        # If there's a connection error (e.g., invalid token), show an error and exit.
        if client.error_message:
            messagebox.showerror("Connection Error", client.error_message)
            return

        # 3. Get the list of active courses
        courses = client.get_active_courses()

        # If there's an error getting the courses, show an error and exit.
        if courses is None:
            messagebox.showerror("Error", client.error_message or "Could not get the course list.")
            return

        # 4. Show the course selection window and wait for the user's choice
        course_win = CourseWindow(courses)
        selected_course_id = course_win.get_selected_course()

        # If the user closes the window without choosing a course, the application exits.
        if not selected_course_id:
            print("No course selected. Exiting.")
            return

        # 5. Open the main application window for the selected course
        main_app_window = MainWindow(client=client, course_id=selected_course_id)
        main_app_window.mainloop()

    def handle_login(self):
        """
        Manages loading existing credentials or requesting new ones
        via the login window.
        """
        credentials = config_manager.load_credentials()

        # If no saved credentials exist, show the login window
        if not credentials:
            login_win = LoginWindow()
            login_win.mainloop()  # Execution pauses here until the window is closed

            # Try to load credentials again in case they were just saved
            credentials = config_manager.load_credentials()

        return credentials


if __name__ == "__main__":
    app = App()