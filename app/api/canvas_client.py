# app/api/canvas_client.py

import requests
from canvasapi import Canvas
from canvasapi.exceptions import InvalidAccessToken, Unauthorized
from app.utils.logger_config import logger


class CanvasClient:
    def __init__(self, canvas_url: str, api_token: str):
        logger.info("Inicializando CanvasClient...")
        self.canvas = None
        self.error_message = None
        self.canvas_url = canvas_url
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

    def create_rubric(self, course_id: int, title: str, criteria_text: str):
        logger.info(f"Intentando crear rúbrica '{title}' en el curso ID: {course_id}")
        if not self.canvas: return False

        parsed_criteria = {}
        try:
            lines = criteria_text.strip().split('\n')
            for i, line in enumerate(lines):
                if not line.strip(): continue
                parts = [p.strip() for p in line.split(',')]
                if len(parts) != 3:
                    self.error_message = f"Error de formato en la línea {i + 1} del criterio. Se esperan 3 partes."
                    logger.error(self.error_message)
                    return False

                description, long_description, points = parts
                parsed_criteria[str(i)] = {
                    'description': description,
                    'long_description': long_description,
                    'points': int(points)
                }
            logger.info(f"Criterios procesados: {parsed_criteria}")
        except (ValueError, IndexError) as e:
            self.error_message = f"Error al procesar los criterios: {e}"
            logger.error(self.error_message)
            return False

        if not parsed_criteria:
            self.error_message = "No se han proporcionado criterios válidos."
            logger.warning(self.error_message)
            return False

        # --- MÉTODO CORREGIDO: Usando 'requests' para un control total ---
        api_url = f"{self.canvas_url}/api/v1/courses/{course_id}/rubrics"
        headers = {'Authorization': f'Bearer {self.api_token}'}

        payload = {
            'rubric': {
                'title': title,
                'criteria': parsed_criteria
            },
            'rubric_association': {
                'association_id': course_id,
                'association_type': 'Course',
                'purpose': 'grading'
            }
        }

        try:
            logger.info(f"Enviando datos de rúbrica a la API: {payload}")
            response = requests.post(api_url, headers=headers, json=payload)

            # Revisar si la respuesta del servidor es un error
            response.raise_for_status()

            logger.info(f"Rúbrica creada con éxito. Respuesta: {response.json()}")
            return True
        except requests.exceptions.RequestException as e:
            self.error_message = f"Error de API al crear la rúbrica: {e}\nRespuesta: {e.response.text if e.response else 'N/A'}"
            logger.error(self.error_message, exc_info=True)
            return False

    # --- El resto de los métodos permanecen sin cambios ---
    def get_active_courses(self):
        if not self.canvas: return None
        try:
            courses = self.canvas.get_courses(enrollment_state="active")
            return [{"id": course.id, "name": course.name} for course in courses]
        except Exception as e:
            self.error_message = f"Error al obtener los cursos: {e}"
            return None

    def create_quiz(self, course_id: int, quiz_settings: dict):
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
        if not self.canvas: return None
        try:
            course = self.get_course(course_id)
            quizzes = course.get_quizzes()
            return [{"id": quiz.id, "title": quiz.title} for quiz in quizzes]
        except Exception as e:
            self.error_message = f"Error al obtener la lista de quizzes clásicos: {e}"
            return None

    def get_new_quizzes(self, course_id: int):
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
            return None

    def get_course(self, course_id: int):
        if not self.canvas: return None
        try:
            return self.canvas.get_course(course_id)
        except Exception as e:
            self.error_message = f"Error al obtener el curso {course_id}: {e}"
            return None

    def get_rubrics(self, course_id: int):
        if not self.canvas:
            return None
        try:
            course = self.get_course(course_id)
            if course:
                rubrics = course.get_rubrics()
                return [{"id": rubric.id, "title": rubric.title} for rubric in rubrics]
            return []
        except Exception as e:
            self.error_message = f"Error al obtener la lista de rúbricas: {e}"
            return None

    def create_assignment(self, course_id: int, assignment_settings: dict):
        """
        Crea una nueva actividad (assignment) en el curso.
        """
        logger.info(f"Intentando crear actividad con configuración: {assignment_settings}")
        if not self.canvas:
            return False

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