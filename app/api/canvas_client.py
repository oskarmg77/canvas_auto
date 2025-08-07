# app/api/canvas_client.py

import requests
import json
from canvasapi import Canvas
from canvasapi.exceptions import InvalidAccessToken, Unauthorized
from app.utils.logger_config import logger

class CanvasClient:
    """
    Gestiona toda la comunicación con la API de Canvas LMS.
    """

    # --------------------------------------------------------------------------
    # INICIALIZACIÓN Y CONEXIÓN
    # --------------------------------------------------------------------------

    def __init__(self, canvas_url: str, api_token: str):
        logger.info("Inicializando CanvasClient...")
        self.canvas = None
        self.error_message = None
        self.canvas_url = canvas_url.rstrip('/')
        self.api_token = api_token
        try:
            self.canvas = Canvas(self.canvas_url, self.api_token)
            user = self.canvas.get_current_user()
            logger.info(f"Conexión exitosa como usuario: {user.name}")
        except (InvalidAccessToken, Unauthorized):
            self.error_message = "Error: Token de acceso inválido o sin autorización."
            logger.error(self.error_message)
        except Exception as e:
            self.error_message = f"No se pudo conectar a Canvas. Verifique la URL.\nError: {e}"
            logger.error(self.error_message)

    # --------------------------------------------------------------------------
    # MÉTODOS RELACIONADOS CON RÚBRICAS
    # --------------------------------------------------------------------------

    def create_rubric(self, course_id: int, title: str, criteria_data: list, options: dict) -> bool:
        """
        Crea una rúbrica completa con todos sus niveles en una sola petición POST,
        asegurando que tanto los criterios como los ratings se envíen como diccionarios indexados.
        """
        logger.info(f"Intentando creación de rúbrica en un solo paso para '{title}'")
        if not self.canvas: return False

        processed_criteria = {}
        for c_idx, crit in enumerate(criteria_data):
            crit_copy = crit.copy()

            # --- CORRECCIÓN FINAL APLICADA ---
            # 1. Convertimos la lista de 'ratings' en un diccionario indexado.
            ratings_list = crit_copy.pop('ratings', [])
            ratings_dict = {}
            for r_idx, rating in enumerate(ratings_list):
                # 2. Nos aseguramos de que los puntos se envíen como string para máxima compatibilidad.
                ratings_dict[str(r_idx)] = {
                    "description": rating.get("description", ""),
                    "long_description": rating.get("long_description", ""),
                    "points": str(rating.get("points", 0))
                }
            crit_copy['ratings'] = ratings_dict
            # --- FIN DE LA CORRECCIÓN ---

            processed_criteria[str(c_idx)] = crit_copy

        if not processed_criteria:
            self.error_message = "No se han proporcionado criterios válidos."
            logger.warning(self.error_message)
            return False

        api_url = f"{self.canvas_url}/api/v1/courses/{course_id}/rubrics"
        headers = {'Authorization': f'Bearer {self.api_token}'}

        full_payload = {
            'rubric': {
                'title': title,
                'criteria': processed_criteria,
                'free_form_criterion_comments': options.get('free_form_criterion_comments', True)
            },
            'rubric_association': {
                'association_id': course_id,
                'association_type': 'Course',
                'purpose': options.get('purpose', 'grading'),
                'hide_score_total': options.get('hide_score_total', False)
            }
        }

        try:
            logger.info(f"Enviando payload completo final (POST) a {api_url}: {json.dumps(full_payload, indent=2)}")
            response = requests.post(api_url, headers=headers, json=full_payload)
            response.raise_for_status()
            logger.info(f"¡ÉXITO! Rúbrica creada correctamente. Respuesta: {response.json()}")
            return True
        except requests.exceptions.RequestException as e:
            self.error_message = f"Error de API al crear la rúbrica: {e}\nRespuesta: {e.response.text if e.response else 'N/A'}"
            logger.error(self.error_message, exc_info=True)
            return False

    def get_rubrics(self, course_id: int) -> list | None:
        """Obtiene una lista de todas las rúbricas asociadas a un curso."""
        if not self.canvas: return None
        try:
            course = self.get_course(course_id)
            if course:
                rubrics = course.get_rubrics()
                return [{"id": rubric.id, "title": rubric.title, "points_possible": rubric.points_possible} for rubric in rubrics]
            return []
        except Exception as e:
            self.error_message = f"Error al obtener la lista de rúbricas: {e}"
            logger.error(self.error_message, exc_info=True)
            return None

    # --------------------------------------------------------------------------
    # OTROS MÉTODOS (Cursos, Quizzes, Actividades)
    # --------------------------------------------------------------------------

    def get_active_courses(self) -> list | None:
        if not self.canvas: return None
        try:
            courses = self.canvas.get_courses(enrollment_state="active")
            return [{"id": course.id, "name": course.name} for course in courses]
        except Exception as e:
            self.error_message = f"Error al obtener los cursos: {e}"
            logger.error(self.error_message, exc_info=True)
            return None

    def get_course(self, course_id: int):
        if not self.canvas: return None
        try:
            return self.canvas.get_course(course_id)
        except Exception as e:
            self.error_message = f"Error al obtener el curso {course_id}: {e}"
            logger.error(self.error_message, exc_info=True)
            return None

    def create_quiz(self, course_id: int, quiz_settings: dict) -> bool:
        if not self.canvas: return False
        try:
            course = self.get_course(course_id)
            if course:
                course.create_quiz(quiz=quiz_settings)
                return True
            return False
        except Exception as e:
            self.error_message = f"Error al crear el quiz clásico: {e}"
            logger.error(self.error_message, exc_info=True)
            return False

    def create_new_quiz(self, course_id: int, settings: dict) -> bool:
        api_url = f"{self.canvas_url}/api/quiz/v1/courses/{course_id}/quizzes"
        headers = {'Authorization': f'Bearer {self.api_token}'}
        payload = {'quiz': settings}
        try:
            response = requests.post(api_url, headers=headers, json=payload)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            self.error_message = f"Error de API al crear el Nuevo Quiz: {e}\nRespuesta: {e.response.text if e.response else 'N/A'}"
            logger.error(self.error_message, exc_info=True)
            return False

    def get_quizzes(self, course_id: int) -> list | None:
        if not self.canvas: return None
        try:
            course = self.get_course(course_id)
            quizzes = course.get_quizzes()
            return [{"id": quiz.id, "title": quiz.title} for quiz in quizzes]
        except Exception as e:
            self.error_message = f"Error al obtener la lista de quizzes clásicos: {e}"
            logger.error(self.error_message, exc_info=True)
            return None

    def get_new_quizzes(self, course_id: int) -> list | None:
        if not self.canvas: return None
        api_url = f"{self.canvas_url}/api/quiz/v1/courses/{course_id}/quizzes"
        headers = {'Authorization': f'Bearer {self.api_token}'}
        try:
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            new_quizzes_data = response.json()
            return [{"id": quiz.get('id'), "title": quiz.get('title')} for quiz in new_quizzes_data]
        except requests.exceptions.RequestException as e:
            self.error_message = f"Error de API al obtener la lista de Nuevos Quizzes: {e}\nRespuesta: {e.response.text if e.response else 'N/A'}"
            logger.error(self.error_message, exc_info=True)
            return None

    def create_assignment(self, course_id: int, assignment_settings: dict) -> bool:
        logger.info(f"Intentando crear actividad con configuración: {assignment_settings}")
        if not self.canvas: return False
        try:
            course = self.get_course(course_id)
            if course:
                new_assignment = course.create_assignment(assignment=assignment_settings)
                logger.info(f"Actividad '{new_assignment.name}' creada con éxito (ID: {new_assignment.id}).")
                return True
            return False
        except Exception as e:
            self.error_message = f"Error de API al crear la actividad: {e}"
            logger.error(self.error_message, exc_info=True)
            return False