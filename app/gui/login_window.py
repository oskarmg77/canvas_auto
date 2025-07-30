# app/gui/login_window.py

import customtkinter as ctk
from app.utils import config_manager


class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Configuración Inicial - Canvas Auto")
        self.geometry("400x250")
        self.resizable(False, False)

        self.grid_columnconfigure(0, weight=1)

        # Marco principal
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)

        # Widgets
        title_label = ctk.CTkLabel(main_frame, text="Conexión con Canvas", font=ctk.CTkFont(size=16, weight="bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        url_label = ctk.CTkLabel(main_frame, text="URL de Canvas:")
        url_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.url_entry = ctk.CTkEntry(main_frame, placeholder_text="https://canvas.instructure.com")
        self.url_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        token_label = ctk.CTkLabel(main_frame, text="Token de Acceso:")
        token_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.token_entry = ctk.CTkEntry(main_frame, show="*")
        self.token_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        self.save_button = ctk.CTkButton(main_frame, text="Guardar y Continuar", command=self.save_and_continue)
        self.save_button.grid(row=3, column=0, columnspan=2, pady=(20, 0))

        self.status_label = ctk.CTkLabel(main_frame, text="", text_color="red")
        self.status_label.grid(row=4, column=0, columnspan=2, pady=(10, 0))

    def save_and_continue(self):
        url = self.url_entry.get().strip()
        token = self.token_entry.get().strip()

        if not url or not token:
            self.status_label.configure(text="Error: Ambos campos son obligatorios.")
            return

        if config_manager.save_credentials(url, token):
            self.destroy()  # Cierra la ventana de login si se guarda con éxito
        else:
            self.status_label.configure(text="Error: No se pudo guardar el archivo.")