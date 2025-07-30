# app/api/canvas_client.py

from canvasapi import Canvas
from canvasapi.exceptions import InvalidAccessToken, Unauthorized


class CanvasClient:
    """
    Gestiona la comunicación con la API de Canvas.
    """

    def __init__(self, canvas_url: str, api_token: str):
        """
        Constructor que SÍ ACEPTA los argumentos 'canvas_url' y 'api_token'.
        """
        self.canvas = None
        self.error_message = None
        try:
            # Inicializa la conexión con la API
            self.canvas = Canvas(canvas_url, api_token)
            # Hacemos una llamada simple para verificar que el token es válido
            self.canvas.get_current_user()
        except (InvalidAccessToken, Unauthorized):
            self.error_message = "Error: Token de acceso inválido o sin autorización."
        except Exception as e:
            self.error_message = f"No se pudo conectar a Canvas. Verifique la URL.\nError: {e}"

    def get_active_courses(self):
        """
        Devuelve una lista de los cursos activos para el usuario actual.
        Cada curso es un diccionario con 'id' y 'name'.
        """
        if not self.canvas:
            return None

        try:
            courses = self.canvas.get_courses(enrollment_state="active")
            # Devolvemos una lista simplificada para que la GUI la maneje fácilmente
            return [{"id": course.id, "name": course.name} for course in courses]
        except Exception as e:
            self.error_message = f"Error al obtener los cursos: {e}"
            return None

    def get_course(self, course_id: int):
        """Obtiene un objeto de curso único por su ID."""
        if not self.canvas:
            return None
        try:
            return self.canvas.get_course(course_id)
        except Exception as e:
            self.error_message = f"Error al obtener el curso {course_id}: {e}"
            return None

    def create_quiz(self, course_id: int, quiz_settings: dict):
        """
        Crea un nuevo quiz en el curso especificado.

        :param course_id: El ID del curso.
        :param quiz_settings: Un diccionario con la configuración del quiz.
        :return: True si se creó con éxito, False en caso contrario.
        """
        if not self.canvas:
            return False

        try:
            course = self.get_course(course_id)
            if course:
                course.create_quiz(quiz=quiz_settings)
                return True
            return False
        except Exception as e:
            self.error_message = f"Error al crear el quiz: {e}"
            return False