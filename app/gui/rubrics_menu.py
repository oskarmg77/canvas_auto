# app/gui/rubrics_menu.py

import customtkinter as ctk
from tkinter import messagebox
from app.utils.logger_config import logger


class RubricsMenu(ctk.CTkFrame):
    def __init__(self, parent, client, course_id, back_callback):
        super().__init__(parent)
        self.client = client
        self.course_id = course_id
        self.back_callback = back_callback

        back_button = ctk.CTkButton(self, text="< Volver al Menú Principal", command=self.back_callback)
        back_button.pack(anchor="nw", padx=10, pady=10)

        self.tab_view = ctk.CTkTabview(self, anchor="w")
        self.tab_view.pack(expand=True, fill="both", padx=10, pady=(0, 10))

        self.tab_view.add("Crear Rúbrica")
        self.tab_view.add("Ver Rúbricas")

        self.setup_create_rubric_tab()
        self.setup_view_rubrics_tab()

    def setup_create_rubric_tab(self):
        # ... (Copia y pega el código exacto de tu función `setup_create_rubric_tab` original aquí)
        rubric_tab = self.tab_view.tab("Crear Rúbrica")
        rubric_tab.grid_columnconfigure(1, weight=1)
        title_label = ctk.CTkLabel(rubric_tab, text="Título de la Rúbrica:")
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        self.rubric_title_entry = ctk.CTkEntry(rubric_tab)
        self.rubric_title_entry.grid(row=0, column=1, padx=20, pady=(20, 10), sticky="ew")
        criteria_label = ctk.CTkLabel(rubric_tab, text="Criterios:")
        criteria_label.grid(row=1, column=0, padx=20, pady=10, sticky="nw")
        instructions_text = "Escribe cada criterio en una nueva línea con el formato:\n\ndescripción corta, descripción larga, puntos\n\nEjemplo:\nOrtografía, El texto no contiene errores ortográficos., 5"
        self.rubric_criteria_textbox = ctk.CTkTextbox(rubric_tab, height=200)
        self.rubric_criteria_textbox.insert("1.0", instructions_text)
        self.rubric_criteria_textbox.grid(row=1, column=1, padx=20, pady=10, sticky="nsew")
        rubric_tab.grid_rowconfigure(1, weight=1)
        create_button = ctk.CTkButton(rubric_tab, text="Crear Rúbrica", command=self.handle_create_rubric)
        create_button.grid(row=2, column=1, padx=20, pady=20, sticky="e")

    def handle_create_rubric(self):
        # ... (Copia y pega el código exacto de tu función `handle_create_rubric` original aquí)
        logger.info("Botón 'Crear Rúbrica' pulsado.")
        title = self.rubric_title_entry.get()
        criteria_text = self.rubric_criteria_textbox.get("1.0", "end-1c")
        if not title or not criteria_text or criteria_text.startswith("Escribe cada criterio"):
            messagebox.showwarning("Campos Requeridos", "El título y los criterios son obligatorios.")
            return
        success = self.client.create_rubric(self.course_id, title, criteria_text)
        if success:
            messagebox.showinfo("Éxito", f"La rúbrica '{title}' ha sido creada correctamente.")
            self.rubric_title_entry.delete(0, "end")
            self.rubric_criteria_textbox.delete("1.0", "end")
        else:
            messagebox.showerror("Error", self.client.error_message or "Ocurrió un error al crear la rúbrica.")

    def setup_view_rubrics_tab(self):
        # ... (Copia y pega el código exacto de tu función `setup_view_rubrics_tab` original aquí)
        view_tab = self.tab_view.tab("Ver Rúbricas")
        view_tab.grid_columnconfigure(0, weight=1)
        view_tab.grid_rowconfigure(1, weight=1)
        action_frame = ctk.CTkFrame(view_tab)
        action_frame.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        refresh_button = ctk.CTkButton(action_frame, text="Cargar Rúbricas", command=self.handle_view_rubrics)
        refresh_button.pack(side="left")
        self.rubric_list_frame = ctk.CTkScrollableFrame(view_tab, label_text="Rúbricas en el Curso")
        self.rubric_list_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

    def handle_view_rubrics(self):
        # ... (Copia y pega el código exacto de tu función `handle_view_rubrics` original aquí)
        logger.info("Botón 'Cargar Rúbricas' pulsado.")
        for widget in self.rubric_list_frame.winfo_children():
            widget.destroy()
        rubrics = self.client.get_rubrics(self.course_id)
        if rubrics is None:
            messagebox.showerror("Error", self.client.error_message or "No se pudo cargar la lista de rúbricas.")
            return
        if not rubrics:
            label = ctk.CTkLabel(self.rubric_list_frame, text="No se encontraron rúbricas en este curso.")
            label.pack(pady=10)
        else:
            for rubric in rubrics:
                label = ctk.CTkLabel(self.rubric_list_frame, text=f"• {rubric['title']} (ID: {rubric['id']})")
                label.pack(anchor="w", padx=10, pady=2)