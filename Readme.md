# Canvas Auto 自动化

Aplicación de escritorio para automatizar tareas en la plataforma Canvas LMS, construida con Python y CustomTkinter.

## Características Actuales ✨

* **Interfaz Gráfica Moderna**: Uso de `customtkinter` para una apariencia atractiva y sencilla.
* **Gestión de Credenciales**: Almacenamiento local de la URL de Canvas y el token de API.
* **Conexión y Verificación**: El cliente de API verifica que las credenciales sean válidas al conectarse.
* **Selección de Cursos**: Muestra una lista de los cursos activos del usuario para que seleccione con cuál desea trabajar.
* **Panel de Control Principal**: Una vez seleccionado un curso, se abre una ventana principal con una interfaz de pestañas para las diferentes herramientas de automatización.
* **Módulo de Quizzes**:
    * **Creación**: Permite crear tanto **Quizzes Clásicos** como **Nuevos Quizzes (New Quizzes)**.
    * **Visualización**: Carga y muestra una lista completa de todos los quizzes existentes en el curso.
* **Módulo de Rúbricas**:
    * **Creación**: Permite crear rúbricas a partir de texto plano, asociándolas correctamente al curso para su visibilidad.
    * **Visualización**: Carga y muestra una lista de todas las rúbricas disponibles para el curso.

## Instalación y Ejecución 🚀

1.  **Clonar el repositorio:**
    ```bash
    git clone <URL-de-tu-repositorio>
    cd canvas_auto
    ```

2.  **Crear y activar un entorno virtual (recomendado):**
    ```bash
    # Windows
    python -m venv .venv
    .venv\Scripts\activate

    # macOS / Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Instalar las dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Ejecutar la aplicación:**
    ```bash
    python main.py
    ```

## Próximos Pasos

* Desarrollar la funcionalidad en la pestaña "Crear Actividad".