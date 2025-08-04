# app/gui/activities_menu.py

import customtkinter as ctk
from tkinter import messagebox
from app.utils.logger_config import logger


class ActivitiesMenu(ctk.CTkFrame):
    def __init__(self, parent, client, course_id, back_callback):
        super().__init__(parent)
        self.client = client
        self.course_id = course_id
        self.back_callback = back_callback

        back_button = ctk.CTkButton(self, text="< Volver al Menú Principal", command=self.back_callback)
        back_button.pack(anchor="nw", padx=10, pady=10)

        # Contenedor principal para centrar el contenido
        container = ctk.CTkFrame(self)
        container.pack(expand=True, fill="both", padx=10, pady=(0, 10))

        # Pestañas para Actividades
        self.tab_view = ctk.CTkTabview(container, anchor="w")
        self.tab_view.pack(expand=True, fill="both")

        self.tab_view.add("Crear Actividad")
        self.setup_activity_tab()

    def setup_activity_tab(self):
        # ... (Copia y pega el código exacto de tu función `setup_activity_tab` original aquí)
        activity_tab = self.tab_view.tab("Crear Actividad")
        activity_tab.grid_columnconfigure(1, weight=1)
        name_label = ctk.CTkLabel(activity_tab, text="Nombre de la Actividad:")
        name_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        self.activity_name_entry = ctk.CTkEntry(activity_tab)
        self.activity_name_entry.grid(row=0, column=1, padx=20, pady=(20, 10), sticky="ew")
        points_label = ctk.CTkLabel(activity_tab, text="Puntos Posibles:")
        points_label.grid(row=1, column=0, padx=20, pady=10, sticky="w")
        self.activity_points_entry = ctk.CTkEntry(activity_tab)
        self.activity_points_entry.grid(row=1, column=1, padx=20, pady=10, sticky="w")
        submission_label = ctk.CTkLabel(activity_tab, text="Tipos de Entrega Online:")
        submission_label.grid(row=2, column=0, padx=20, pady=10, sticky="nw")
        submission_frame = ctk.CTkFrame(activity_tab)
        submission_frame.grid(row=2, column=1, padx=20, pady=10, sticky="w")
        self.sub_type_upload = ctk.CTkCheckBox(submission_frame, text="Subir archivo (online_upload)")
        self.sub_type_upload.pack(anchor="w", padx=10, pady=5)
        self.sub_type_text = ctk.CTkCheckBox(submission_frame, text="Entrada de texto (online_text_entry)")
        self.sub_type_text.pack(anchor="w", padx=10, pady=5)
        self.sub_type_url = ctk.CTkCheckBox(submission_frame, text="URL de un sitio web (online_url)")
        self.sub_type_url.pack(anchor="w", padx=10, pady=5)
        desc_label = ctk.CTkLabel(activity_tab, text="Descripción:")
        desc_label.grid(row=3, column=0, padx=20, pady=10, sticky="nw")
        self.activity_desc_textbox = ctk.CTkTextbox(activity_tab, height=150)
        self.activity_desc_textbox.grid(row=3, column=1, padx=20, pady=10, sticky="nsew")
        activity_tab.grid_rowconfigure(3, weight=1)
        create_button = ctk.CTkButton(activity_tab, text="Crear Actividad", command=self.handle_create_activity)
        create_button.grid(row=4, column=1, padx=20, pady=20, sticky="e")

    def handle_create_activity(self):
        # ... (Copia y pega el código exacto de tu función `handle_create_activity` original aquí)
        logger.info("Botón 'Crear Actividad' pulsado.")
        name = self.activity_name_entry.get()
        points = self.activity_points_entry.get()
        description = self.activity_desc_textbox.get("1.0", "end-1c")
        submission_types = []
        if self.sub_type_upload.get(): submission_types.append('online_upload')
        if self.sub_type_text.get(): submission_types.append('online_text_entry')
        if self.sub_type_url.get(): submission_types.append('online_url')
        if not submission_types:
            messagebox.showwarning("Campo Requerido", "Debes seleccionar al menos un tipo de entrega.")
            return
        activity_settings = {
            'name': name,
            'submission_types': submission_types,
            'description': description,
            'published': False
        }
        try:
            if points:
                activity_settings['points_possible'] = int(points)
        except ValueError:
            messagebox.showwarning("Valor Inválido", "Los puntos deben ser un número.")
            return
        success = self.client.create_assignment(self.course_id, activity_settings)
        if success:
            messagebox.showinfo("Éxito", f"La actividad '{name}' ha sido creada correctamente.")
            self.activity_name_entry.delete(0, "end")
            self.activity_points_entry.delete(0, "end")
            self.activity_desc_textbox.delete("1.0", "end")
            self.sub_type_upload.deselect()
            self.sub_type_text.deselect()
            self.sub_type_url.deselect()
        else:
            messagebox.showerror("Error", self.client.error_message or "Ocurrió un error al crear la actividad.")