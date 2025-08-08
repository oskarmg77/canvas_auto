# app/api/canvas_client.py
import json
import csv
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

    # --------------------------------------------------------------------- #
    # 2. Rúbricas
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
    # 2. Cursos (helpers para la GUI principal)
    # ------------------------------------------------------------------ #
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


    # ------------------------------------------------------------------ #
    # 3. Exportación CSV
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
