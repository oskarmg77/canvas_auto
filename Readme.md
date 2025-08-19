# Canvas Auto

Aplicación de escritorio para automatizar tareas en la plataforma Canvas LMS, construida con Python y CustomTkinter.

## Características Actuales ✨

* **Interfaz Gráfica Moderna**: Uso de `customtkinter` para una apariencia atractiva y fluida.
* **Menú Principal tipo Dashboard**: Una vez seleccionado un curso, se presenta un menú principal de tarjetas interactivas y visuales que mejoran la experiencia de usuario.
* **Iconos Personalizados**: Cada opción del menú cuenta con iconos únicos que representan su función.
* **Gestión de Credenciales**: Almacenamiento local y seguro de la URL de Canvas y el token de API.
* **Conexión y Verificación**: El cliente de API verifica que las credenciales sean válidas al conectarse.
* **Selección de Cursos**: Muestra una lista de los cursos activos del usuario para que seleccione con cuál desea trabajar, con la opción de cambiar de curso sin reiniciar la aplicación.
* **Módulos de Gestión por Submenús**:
    * **Gestión de Quizzes**:
        -   Crear **Quizzes Clásicos** o **Nuevos Quizzes (New Quizzes)**.
        -   **Creación masiva de preguntas** para "Nuevos Quizzes" a partir de un formato JSON, ideal para usar con la salida de herramientas de IA.
        -   Visualizar una lista completa de los quizzes existentes, manejando la paginación de la API para garantizar que no falte ninguno.
    * **Gestión de Rúbricas**:
        -   Crear rúbricas a partir de texto, CSV o JSON.
        -   Soporte para **criterios con múltiples niveles de logro** (ratings).
        -   Admite **valores decimales** en puntuaciones, con coma o punto.
        -   Importar rúbricas desde **CSV exportados de Canvas** o creados manualmente.
        -   Exportar rúbricas existentes del curso a **CSV compatible** para su reutilización.
    * **Gestión de Actividades**:
        -   Crear tareas definiendo nombre, puntos, descripción y tipos de entrega online.
        -   **Descarga Inteligente de Entregas**:
            -   Visualización de actividades **agrupadas por categorías** tal como en la plataforma.
            -   Al seleccionar una actividad, se muestra un **resumen previo** con el número de entregas, cuántas tienen PDF y si hay una rúbrica asociada.
            -   **Confirmación del usuario** antes de iniciar la descarga para evitar procesos innecesarios.
            -   **Información de progreso en tiempo real** durante la descarga.
            -   **Descarga automática de rúbricas** asociadas en formatos JSON y CSV.
            -   **Nombres de carpeta abreviados** y saneados para cursos y tareas, evitando errores de rutas largas en Windows.
            -   Sobrescritura automática de archivos existentes sin preguntar.

### Formato JSON para Preguntas de Quiz

Para usar la creación masiva de preguntas, proporciona un JSON con la siguiente estructura. Puedes pegar una lista de preguntas `[...]` o un objeto `{"items": [...]}`.

El siguiente ejemplo muestra todos los campos disponibles:

```json
{
  "items": [
    {
      "question": "Texto de la pregunta principal (ej: ¿Cuál es la capital de España?)",
      "choices": [
        "Barcelona",
        "Madrid",
        "Lisboa",
        "Sevilla"
      ],
      "correct": "B",
      "points": 1.5,
      "feedback_correct": "¡Correcto! Madrid es la capital.",
      "feedback_incorrect": "Respuesta incorrecta. La capital es Madrid.",
      "answer_feedback": {
        "C": "Lisboa es la capital de Portugal, no de España."
      }
    }
  ]
}




```
canvas_auto/
├── app/                    # Módulo principal de la aplicación
│ ├── api/                  # Comunicación con la API de Canvas LMS
│ │ ├── init.py             # Inicializador del paquete API
│ │ └── canvas_client.py    # Cliente para interactuar con la API de Canvas
│ ├── assets/               # Recursos gráficos y estáticos
│ │ └── icons/              # Iconos usados en la interfaz gráfica
│ │ ├── activity_icon.png   # Icono para actividades
│ │ ├── course_icon.png     # Icono para cursos
│ │ ├── quiz_icon.png       # Icono para quizzes
│ │ └── rubric_icon.png     # Icono para rúbricas
│ ├── core/                 # Lógica de negocio o automatizaciones
│ │ ├── init.py             # Inicializador del paquete core
│ │ └── automation.py       # Funciones de automatización (pendientes o en uso)
│ ├── gui/                  # Módulos de la interfaz gráfica (CustomTkinter)
│ │ ├── logs/               # Carpeta para logs específicos de GUI (si aplica)
│ │ ├── init.py             # Inicializador del paquete GUI
│ │ ├── activities_menu.py  # Pantalla de gestión de actividades
│ │ ├── course_window.py    # Pantalla de selección de curso
│ │ ├── login_window.py     # Pantalla de inicio de sesión
│ │ ├── main_window.py      # Ventana principal del dashboard
│ │ ├── quizzes_menu.py     # Pantalla de gestión de quizzes
│ │ └── rubrics_menu.py     # Pantalla de gestión de rúbricas (creación, importación/exportación)
│ └── utils/                # Utilidades generales
│ ├── init.py               # Inicializador del paquete utils
│ ├── config_manager.py     # Gestión de configuración y credenciales
│ ├── export_utils.py       # Funciones de exportación de datos
│ └── logger_config.py      # Configuración del sistema de logs
├── logs/                   # Carpeta de logs generales de la aplicación
│ └── canvas_auto.log       # Archivo de log principal
├── .env                    # Variables de entorno (no se sube a Git)
├── .gitignore              # Archivos y carpetas ignorados por Git
├── config.json             # Configuración y credenciales guardadas localmente
├── main.py                 # Punto de entrada de la aplicación
├── Readme.md               # Documentación del proyecto
└── requirements.txt        # Lista de dependencias necesarias
```


## Instalación y Ejecución 🚀

1. **Clonar el repositorio:**
    ```bash
    git clone <URL-de-tu-repositorio>
    cd canvas_auto
    ```

2. **Crear y activar un entorno virtual (recomendado):**
    ```bash
    # Windows
    python -m venv .venv
    .venv\Scripts\activate

    # macOS / Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3. **Instalar las dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4. **Ejecutar la aplicación:**
    ```bash
    python main.py
    ```

## Próximos Pasos

* Añadir más opciones avanzadas a la creación de actividades (fechas de entrega, publicación, etc.).
* Implementar la edición o eliminación de elementos ya creados.
* Refinar la interfaz de usuario.
* Soporte para duplicar rúbricas entre cursos directamente.
* Vista previa enriquecida para rúbricas importadas antes de crearlas.
