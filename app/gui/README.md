# Canvas Auto-Evaluator

Una herramienta de escritorio para automatizar la descarga y evaluación de entregas de la plataforma Canvas LMS usando la IA de Google Gemini.

## Características Principales

- **Integración con Canvas LMS:**
  - Navega y lista cursos y actividades.
  - Descarga automáticamente todas las entregas (incluyendo historial) de una actividad, organizándolas en carpetas por alumno.
  - Exporta las rúbricas de evaluación asociadas.

- **Evaluación Inteligente con IA (Google Gemini):**
  - Utiliza el modelo multimodal Gemini 1.5 Flash para analizar archivos PDF.
  - Evalúa el contenido del PDF contra la rúbrica de la actividad.
  - Genera un informe detallado en formato CSV con puntuaciones y justificaciones por cada criterio.

- **Sistema Robusto y Eficiente (Nuevas Mejoras):**
  - **Control de Ritmo Adaptativo:** Se autorregula para respetar los límites de la API de Gemini (QPS y cuota diaria), reduciendo la velocidad si es necesario en lugar de fallar. Ideal para la capa gratuita.
  - **Caché de Múltiples Niveles:**
    - **Caché de Subida:** Evita volver a subir el mismo PDF a la API de Gemini si no ha cambiado.
    - **Caché de Resultados:** Guarda los resultados de las evaluaciones y los reutiliza si se vuelve a procesar el mismo archivo, ahorrando tiempo y una cantidad significativa de peticiones a la API.
  - **Proceso Cancelable:** Permite al usuario cancelar una evaluación en curso de forma segura.

- **Interfaz Gráfica de Usuario:**
  - Desarrollada con CustomTkinter para una apariencia moderna.
  - Proporciona feedback en tiempo real a través de una barra de estado y de progreso.

## Instalación

1.  **Clonar el repositorio:**
    ```bash
    git clone <URL_DEL_REPOSITORIO>
    cd <NOMBRE_DEL_REPOSITORIO>
    ```

2.  **Crear un entorno virtual:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # En Windows: .venv\Scripts\activate
    ```

3.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configuración:**
    - Crea un archivo `config.json` en la raíz del proyecto.
    - Añade tus claves de API dentro del archivo con la siguiente estructura:
      ```json
      {
        "canvas_api_url": "https://tu-institucion.instructure.com",
        "canvas_api_key": "TU_API_KEY_DE_CANVAS",
        "gemini_api_key": "TU_API_KEY_DE_GEMINI"
      }
      ```

## Uso

1.  **Ejecutar la aplicación:**
    ```bash
    python main.py
    ```
2.  **Seleccionar un curso:** La aplicación cargará tus cursos disponibles.
3.  **Navegar a la pestaña "Descargar Entregas".**
4.  **Seleccionar una actividad:** Se mostrará un resumen de las entregas.
5.  **Iniciar la evaluación:**
    - Haz clic en "Evaluar con IA (Gemini)".
    - Selecciona una carpeta base donde se guardarán los archivos.
    - El proceso comenzará, descargando los PDFs, subiéndolos a Gemini (si no están en caché) y evaluándolos.
6.  **Revisar los resultados:** Al finalizar, encontrarás un archivo `evaluaciones_gemini.csv` en la carpeta de la actividad con el desglose de la evaluación.

## Detalles Técnicos del Proceso de Evaluación

El flujo de evaluación ha sido optimizado para ser resiliente y eficiente:

1.  **Descarga y Hash:** Se descargan los PDFs de las entregas y se calcula un hash SHA256 para cada uno.
2.  **Caché de Resultados:** Se comprueba si ya existe una evaluación para ese hash en el archivo local `evaluaciones_cache.json`. Si existe, se reutiliza y se salta la llamada a la API.
3.  **Caché de Subida:** Si no hay resultado en caché, se comprueba si el archivo ya fue subido a la API de Gemini (usando `.gemini_file_cache.json`). Si es así, se reutiliza la referencia remota.
4.  **Evaluación en Paralelo Adaptativo:** Las nuevas evaluaciones se procesan en paralelo. Un `RateController` gestiona la velocidad de las peticiones. Si la API devuelve un error de límite de cuota (429), el controlador reduce automáticamente el número de hilos paralelos y reintenta, evitando un fallo total.
5.  **Persistencia:** Los nuevos resultados se guardan tanto en el CSV final como en el archivo de caché para futuras ejecuciones.