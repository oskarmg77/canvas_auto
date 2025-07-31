# Canvas Auto 自动化

Aplicación de escritorio para automatizar tareas en la plataforma Canvas LMS, construida con Python y CustomTkinter.

## Características Actuales ✨

* **Interfaz Gráfica Moderna**: Uso de `customtkinter` para una apariencia atractiva y sencilla.
* **Gestión de Credenciales**: Almacenamiento local de la URL de Canvas y el token de API.
* **Conexión y Verificación**: El cliente de API verifica que las credenciales sean válidas al conectarse.
* **Selección de Cursos**: Muestra una lista de los cursos activos del usuario para que seleccione con cuál desea trabajar.
* **Panel de Control Principal**: Una vez seleccionado un curso, se abre una ventana principal con una interfaz de pestañas para las diferentes herramientas de automatización.
* **Creación de Quizzes**: Implementada la funcionalidad completa en la pestaña "Crear Quiz".
    * Permite definir un título y una descripción.
    * Incluye una opción para elegir entre crear un **Quiz Clásico** o un **Nuevo Quiz (New Quiz)**.
* **Visualización de Quizzes**: Nueva pestaña para cargar y mostrar una lista de los quizzes clásicos existentes en el curso.

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

* Ampliar la pestaña "Ver Quizzes" para que muestre también los "Nuevos Quizzes".
* Desarrollar las funcionalidades en las pestañas "Crear Rúbrica" y "Crear Actividad".