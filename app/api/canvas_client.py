# app/api/canvas_client.py

import requests
from canvasapi import Canvas
from canvasapi.exceptions import InvalidAccessToken, Unauthorized


class CanvasClient:
    """
    Gestiona la comunicación con la API de Canvas.
    """

    def __init__(self, canvas_url: str, api_token: str):
        self.canvas = None
        self.error_message = None

        self.canvas_url = canvas_url
        self.api_token = api_token

        try:
            self.canvas = Canvas(self.canvas_url, self.api_token)
            self.canvas.get_current_user()
        except (InvalidAccessToken, Unauthorized):
            self.error_message = "Error: Token de acceso inválido o sin autorización."
        except Exception as e:
            self.error_message = f"No se pudo conectar a Canvas. Verifique la URL.\nError: {e}"

    # --- MÉTODO AÑADIDO DE VUELTA ---
    def get_active_courses(self):
        """
        Devuelve una lista de los cursos activos para el usuario actual.
        Cada curso es un diccionario con 'id' y 'name'.
        """
        if not self.canvas:
            return None

        try:
            courses = self.canvas.get_courses(enrollment_state="active")
            return [{"id": course.id, "name": course.name} for course in courses]
        except Exception as e:
            self.error_message = f"Error al obtener los cursos: {e}"
            return None

    # --------------------------------

    def create_quiz(self, course_id: int, quiz_settings: dict):
        """Crea un Quiz Clásico."""
        if not self.canvas: return False
        try:
            course = self.get_course(course_id)
            if course:
                course.create_quiz(quiz=quiz_settings)
                return True
            return False
        except Exception as e:
            self.error_message = f"Error al crear el quiz clásico: {e}"
            return False

    def create_new_quiz(self, course_id: int, settings: dict):
        """
        Crea un "Nuevo Quiz" (New Quiz) haciendo una llamada directa a la API.
        Basado en la documentación: POST /api/quiz/v1/courses/:course_id/quizzes
        """
        api_url = f"{self.canvas_url}/api/quiz/v1/courses/{course_id}/quizzes"
        headers = {'Authorization': f'Bearer {self.api_token}'}
        payload = {
            'quiz': {
                'title': settings.get('title'),
                'instructions': settings.get('description'),
                'published': settings.get('published', False)
            }
        }

        try:
            response = requests.post(api_url, headers=headers, json=payload)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            self.error_message = f"Error de API al crear el Nuevo Quiz: {e}\nRespuesta: {e.response.text if e.response else 'N/A'}"
            return False

    def get_quizzes(self, course_id: int):
        """Obtiene una lista de todos los quizzes CLÁSICOS de un curso."""
        if not self.canvas: return None
        try:
            course = self.get_course(course_id)
            quizzes = course.get_quizzes()
            return [{"id": quiz.id, "title": quiz.title} for quiz in quizzes]
        except Exception as e:
            self.error_message = f"Error al obtener la lista de quizzes: {e}"
            return None

    def get_course(self, course_id: int):
        """Obtiene un objeto de curso único por su ID."""
        if not self.canvas: return None
        try:
            return self.canvas.get_course(course_id)
        except Exception as e:
            self.error_message = f"Error al obtener el curso {course_id}: {e}"
            return None