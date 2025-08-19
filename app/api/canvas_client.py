# app/api/canvas_client.py
import json
import csv
import os
import re
import uuid
from pathlib import Path
from typing import List, Dict, Any

import requests
from canvasapi import Canvas
from canvasapi.exceptions import InvalidAccessToken, Unauthorized
from app.utils.logger_config import logger


class CanvasClient:
    """
    Cliente unificado para Canvas LMS.
    Incluye:
    • Creación de rúbricas con múltiples niveles
    • Exportación de rúbricas a CSV
    """

    @staticmethod
    def _sanitize_url(raw: str) -> str:
        return (raw or "").strip().rstrip("/")

    @staticmethod
    def _sanitize_token(raw: str) -> str:
        t = (raw or "")
        # quita prefijo "Bearer " si el usuario lo pegó
        if t.lower().startswith("bearer "):
            t = t[7:]
        # elimina TODOS los espacios/blancos (incl. \r \n \t)
        t = re.sub(r"\s+", "", t)
        return t

    # --------------------------------------------------------------------- #
    # 1. Inicialización
    # --------------------------------------------------------------------- #
    def __init__(self, canvas_url: str, api_token: str):
        self.canvas_url = canvas_url.rstrip("/")
        self.api_token = api_token
        self.error_message: str | None = None

        try:
            self.canvas = Canvas(self.canvas_url, self.api_token)
            user = self.canvas.get_current_user()
            logger.info(f"Conectado a Canvas como «{user.name}»")
        except (InvalidAccessToken, Unauthorized):
            self.canvas = None
            self.error_message = "Token de acceso inválido o sin permisos."
            logger.error(self.error_message)
        except Exception as e:  # pragma: no cover
            self.canvas = None
            self.error_message = f"No se pudo conectar a Canvas ({e})"
            logger.error(self.error_message)

    def _auth_headers(self) -> dict:
        # usa siempre el token saneado
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def _get_paginated_data(self, url: str, params: dict = None) -> list:
        """
        Realiza peticiones GET a un endpoint paginado y devuelve todos los resultados.
        Maneja la paginación siguiendo los encabezados 'Link' de Canvas.
        """
        if params is None:
            params = {}

        results = []
        next_url = url

        try:
            while next_url:
                # Los parámetros solo se envían en la primera petición
                current_params = params if next_url == url else None
                response = requests.get(
                    next_url, headers=self._auth_headers(), params=current_params, timeout=30
                )
                response.raise_for_status()
                data = response.json()
                results.extend(data)

                next_link = response.links.get("next")
                next_url = next_link["url"] if next_link else None

        except requests.RequestException as e:
            logger.error(f"Error durante la paginación para {url}: {e}")
            return []
        return results

    # --------------------------------------------------------------------- #
    # 2. Cursos, Actividades y Entregas
    # --------------------------------------------------------------------- #
    def get_active_courses(self) -> list[dict] | None:
        """
        Devuelve todos los cursos en los que el usuario está activo.
        Formato: [{'id': 123, 'name': 'Nombre del curso'}, ...]
        """
        if not self.canvas:
            return None
        try:
            courses = self.canvas.get_courses(enrollment_state="active")
            return [{"id": c.id, "name": c.name} for c in courses]
        except Exception as exc:
            self.error_message = f"Error al obtener cursos: {exc}"
            logger.error(self.error_message, exc_info=True)
            return None

    def get_course(self, course_id: int):
        """Wrapper fino para reutilizar en otros métodos."""
        if not self.canvas:
            return None
        try:
            return self.canvas.get_course(course_id)
        except Exception as exc:
            self.error_message = f"No se pudo obtener el curso {course_id}: {exc}"
            logger.error(self.error_message, exc_info=True)
            return None

    def get_assignment(self, course_id: int, assignment_id: int) -> Dict[str, Any] | None:
        """Obtiene los detalles de una actividad específica."""
        if not self.canvas:
            return None
        try:
            url = f"{self.canvas_url}/api/v1/courses/{course_id}/assignments/{assignment_id}"
            response = requests.get(url, headers=self._auth_headers(), timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.error_message = f"Error al obtener la actividad {assignment_id}: {e}"
            logger.error(self.error_message)
            return None

    def get_assignments(self, course_id: int) -> List[Dict[str, Any]]:
        """Obtiene una lista de todas las actividades para un curso específico."""
        if not self.canvas:
            return []
        try:
            url = f"{self.canvas_url}/api/v1/courses/{course_id}/assignments"
            return self._get_paginated_data(url, params={"per_page": 100})
        except Exception as e:
            logger.error(f"Error al obtener las actividades para el curso {course_id}: {e}")
            return []

    def get_assignment_groups_with_assignments(self, course_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene los grupos de actividades de un curso, incluyendo las actividades de cada grupo.
        """
        if not self.canvas:
            return []
        try:
            # Usamos el endpoint de grupos de actividades con el parámetro 'include'
            # para que la API nos devuelva las actividades anidadas en cada grupo.
            # Esto es más eficiente que hacer una petición por cada grupo.
            url = f"{self.canvas_url}/api/v1/courses/{course_id}/assignment_groups"
            params = {"include[]": "assignments", "per_page": 100}
            return self._get_paginated_data(url, params=params)
        except Exception as e:
            logger.error(f"Error al obtener los grupos de actividades para el curso {course_id}: {e}")
            return []

    def get_assignment_submission_summary(
        self, course_id: int, assignment_id: int
    ) -> Dict[str, Any] | None:
        """
        Obtiene un resumen de las entregas para una actividad, incluyendo
        conteo de entregas, si tiene rúbrica y si hay PDFs.
        """
        try:
            assignment = self.get_assignment(course_id, assignment_id)
            if not assignment:
                # El mensaje de error ya está establecido por get_assignment
                return None

            submissions = self.get_all_submissions(course_id, assignment_id)

            # Contamos cuántos alumnos únicos han entregado al menos un PDF
            students_with_pdf = set()
            for sub in submissions:
                user_id = sub.get("user_id")
                if user_id in students_with_pdf:
                    continue

                all_attachments = sub.get("attachments", [])
                for history_item in sub.get("submission_history", []):
                    all_attachments.extend(history_item.get("attachments", []))

                if any(att.get("filename", "").lower().endswith(".pdf") for att in all_attachments):
                    students_with_pdf.add(user_id)

            has_rubric = "rubric" in assignment and assignment["rubric"] is not None
            rubric_id = assignment.get("rubric_settings", {}).get("id") if has_rubric else None

            return {
                "submission_count": len(submissions),
                "pdf_submission_count": len(students_with_pdf),
                "has_rubric": has_rubric,
                "rubric_id": rubric_id,
            }
        except Exception as e:
            self.error_message = f"Error al obtener el resumen de la actividad {assignment_id}: {e}"
            logger.error(self.error_message, exc_info=True)
            return None

    def get_all_submissions(self, course_id: int, assignment_id: int) -> List[Dict[str, Any]]:
        """Obtiene todas las entregas para una actividad específica."""
        if not self.canvas:
            return []
        try:
            url = f"{self.canvas_url}/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions"
            params = {"include[]": ["user", "submission_history"], "per_page": 100}
            return self._get_paginated_data(url, params=params)
        except Exception as e:
            logger.error(f"Error al obtener las entregas para la actividad {assignment_id}: {e}")
            return []

    def download_file(self, url: str, folder_path: str, filename: str) -> bool:
        """Descarga un único archivo desde una URL y lo guarda en una ruta específica."""
        try:
            os.makedirs(folder_path, exist_ok=True)
            file_path = os.path.join(folder_path, filename)
            headers = {'Authorization': f'Bearer {self.api_token}'}
            with requests.get(url, headers=headers, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(file_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            logger.info(f"Archivo descargado: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error al descargar el archivo {url}: {e}")
            return False

    # --------------------------------------------------------------------- #
    # 3. Rúbricas
    # --------------------------------------------------------------------- #
    def _build_criteria_dict(self, criteria: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Convierte la lista de criterios del builder en diccionario indexado,
        añadiendo ids únicos a criterios y ratings (requisito Canvas).
        """
        result: Dict[str, Any] = {}

        for c_idx, crit in enumerate(criteria):
            crit_id = f"_{uuid.uuid4().hex[:6]}"
            ratings_src = crit.pop("ratings", [])
            ratings_dict: Dict[str, Any] = {}

            for r_idx, rating in enumerate(ratings_src):
                ratings_dict[str(r_idx)] = {
                    "id": rating.get("id") or f"rating_{c_idx}_{r_idx}",
                    "criterion_id": crit_id,
                    "description": rating["description"],
                    "long_description": rating.get("long_description", ""),
                    "points": str(rating["points"]),
                }

            result[str(c_idx)] = {
                "id": crit_id,
                "description": crit["description"],
                "long_description": crit.get("long_description", ""),
                "points": str(crit["points"]),
                "criterion_use_range": crit.get("criterion_use_range", False),
                "ratings": ratings_dict,
            }

        return result

    def create_rubric(
        self,
        course_id: int,
        title: str,
        criteria: List[Dict[str, Any]],
        options: Dict[str, Any],
    ) -> bool:
        """
        Crea una rúbrica completa (criterios + niveles) en el curso indicado.
        `criteria` viene de la GUI; cada criterio incluye una lista “ratings”.
        """
        if not self.canvas:
            return False

        payload = {
            "rubric": {
                "title": title,
                "criteria": self._build_criteria_dict(criteria),
                "free_form_criterion_comments": options.get(
                    "free_form_criterion_comments", True
                ),
            },
            "rubric_association": {
                "association_id": course_id,
                "association_type": "Course",
                "purpose": options.get("purpose", "grading"),
                "hide_score_total": options.get("hide_score_total", False),
            },
        }

        url = f"{self.canvas_url}/api/v1/courses/{course_id}/rubrics"
        headers = {"Authorization": f"Bearer {self.api_token}"}

        try:
            logger.info(f"POST {url}\n{json.dumps(payload, indent=2, ensure_ascii=False)}")
            r = requests.post(url, headers=headers, json=payload, timeout=30)
            r.raise_for_status()
            logger.info("✔ Rúbrica creada correctamente")
            return True
        except requests.RequestException as exc:
            self.error_message = f"Error al crear rúbrica ({exc})"
            logger.error(self.error_message)
            return False

    def export_rubric_to_json(self, course_id: int, rubric_id: int, out_path: Path | str) -> bool:
        """
        Descarga la rúbrica indicada y la guarda en JSON (datos crudos de la API).
        """
        out_path = Path(out_path)
        try:
            course = self.get_course(course_id)
            if course is None:
                return False

            # get_rubric con include=['assessments'] para datos completos
            rubric = course.get_rubric(rubric_id, include=["assessments"])

            # El objeto de la rúbrica tiene los datos en el diccionario _attributes
            rubric_data = rubric._attributes

            with out_path.open("w", encoding="utf-8") as f:
                json.dump(rubric_data, f, ensure_ascii=False, indent=4)

            logger.info(f"JSON de la rúbrica exportado correctamente → {out_path}")
            return True
        except Exception as exc:
            self.error_message = f"No se pudo exportar la rúbrica a JSON ({exc})"
            logger.error(self.error_message, exc_info=True)
            return False

    def get_rubrics(self, course_id: int):
        if not self.canvas:
            return None
        try:
            course = self.canvas.get_course(course_id)
            return [
                {"id": r.id, "title": r.title, "points_possible": r.points_possible}
                for r in course.get_rubrics()
            ]
        except Exception as exc:
            self.error_message = f"Error al listar rúbricas ({exc})"
            logger.error(self.error_message)
            return None

    # ------------------------------------------------------------------ #
    # 4. Exportación CSV
    # ------------------------------------------------------------------ #
    def export_rubric_to_csv(
        self, course_id: int, rubric_id: int, out_path: Path | str
    ) -> bool:
        """
        Descarga la rúbrica indicada y la guarda en CSV (formato Canvas).
        Soporta tanto los objetos devueltos por canvasapi (dicts) como los
        que puedan venir como instancias con atributos.
        """
        out_path = Path(out_path)

        try:
            course = self.get_course(course_id)
            if course is None:
                return False

            rubric = course.get_rubric(rubric_id)

            # --- helper para abstraer acceso a 'ratings' y otros campos ----
            def get(field: str, crit, default=None):
                # crit puede ser dict o un objeto con atributos
                if isinstance(crit, dict):
                    return crit.get(field, default)
                return getattr(crit, field, default)

            # 1. obtener nº máx. de niveles
            max_ratings = max(len(get("ratings", c, [])) for c in rubric.data)

            # 2. cabeceras dinámicas
            headers = [
                "Rubric Name",
                "Criteria Name",
                "Criteria Description",
                "Criteria Points",
            ]
            for i in range(max_ratings):
                headers += [
                    f"Rating {i+1} Name",
                    f"Rating {i+1} Description",
                    f"Rating {i+1} Points",
                ]

            # 3. escritura CSV
            with out_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)

                for c in rubric.data:
                    row = [
                        rubric.title,
                        get("description", c, ""),
                        get("long_description", c, ""),
                        get("points", c, ""),
                    ]

                    for r in get("ratings", c, []):
                        row += [
                            get("description", r, ""),
                            get("long_description", r, ""),
                            get("points", r, ""),
                        ]

                    writer.writerow(row)

            logger.info(f"CSV exportado correctamente → {out_path}")
            return True

        except Exception as exc:
            self.error_message = f"No se pudo exportar rúbrica ({exc})"
            logger.error(self.error_message, exc_info=True)
            return False
