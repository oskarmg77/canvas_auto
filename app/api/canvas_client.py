# app/api/canvas_client.py
import json
import csv
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

    # --------------------------------------------------------------------- #
    # 4. Quizzes (Classic y New Quizzes)
    # --------------------------------------------------------------------- #
    def _auth_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def _nq_base(self, course_id: int) -> str:
        return f"{self.canvas_url}/api/quiz/v1/courses/{course_id}"

    # -------- Classic Quizzes (API v1) ----------------------------------- #
    def get_quizzes(self, course_id: int) -> list[dict] | None:
        """
        Lista Quizzes Clásicos del curso (API v1, canvasapi).
        """
        if not self.canvas:
            return None
        try:
            course = self.canvas.get_course(course_id)
            quizzes = course.get_quizzes()
            out = []
            for q in quizzes:
                out.append({"id": q.id, "title": q.title, "type": "classic"})
            return out
        except Exception as exc:
            self.error_message = f"No se pudieron obtener los quizzes clásicos: {exc}"
            logger.error(self.error_message, exc_info=True)
            return None

    def create_quiz(self, course_id: int, settings: dict) -> bool:
        """
        Crea un Quiz Clásico (API v1).
        settings típicos: { 'title', 'description', 'quiz_type'='assignment', ... }
        """
        if not self.canvas:
            return False
        try:
            course = self.canvas.get_course(course_id)
            # canvasapi usa 'description' para el enunciado del quiz clásico
            course.create_quiz(quiz={
                "title": settings.get("title", ""),
                "description": settings.get("description", ""),
                "quiz_type": settings.get("quiz_type", "assignment"),
                "published": settings.get("published", False),
            })
            return True
        except Exception as exc:
            self.error_message = f"No se pudo crear el quiz clásico: {exc}"
            logger.error(self.error_message, exc_info=True)
            return False

    # -------- New Quizzes (quiz/v1) -------------------------------------- #
    def get_new_quizzes(self, course_id: int) -> list[dict] | None:
        """
        Lista New Quizzes del curso (quiz/v1), manejando la paginación.
        OJO: en New Quizzes el 'id' devuelto es el assignment_id usable en /items.
        """
        try:
            all_new_quizzes = []  # 1. Lista para acumular los resultados
            url = f"{self._nq_base(course_id)}/quizzes"

            # 2. Bucle para seguir las páginas 'next' hasta que no haya más
            while url:
                r = requests.get(url, headers=self._auth_headers(), timeout=30)
                r.raise_for_status()
                data = r.json() or []

                # 3. Acumular los quizzes de la página actual
                all_new_quizzes.extend(
                    [{"id": q.get("id"), "title": q.get("title"), "type": "new"} for q in data]
                )

                # 4. Buscar el enlace a la siguiente página en las cabeceras
                # La librería 'requests' convenientemente parsea el header 'Link'
                next_link = r.links.get('next')
                if next_link:
                    url = next_link.get('url')
                else:
                    url = None # 5. Si no hay más páginas, terminamos el bucle

            return all_new_quizzes

        except Exception as exc:
            self.error_message = f"No se pudieron obtener los New Quizzes: {exc}"
            logger.error(self.error_message, exc_info=True)
            return None

    def create_new_quiz(self, course_id: int, settings: dict) -> bool:
        """
        Crea un New Quiz vacío (quiz/v1). Devuelve True/False.
        """
        try:
            url = f"{self._nq_base(course_id)}/quizzes"
            payload = {
                "quiz": {
                    "title": settings.get("title", ""),
                    "instructions": settings.get("description", ""),
                    "published": settings.get("published", False),
                    # puedes pasar 'points_possible', 'grading_type', 'quiz_settings', etc.
                }
            }
            r = requests.post(url, headers=self._auth_headers(), json=payload, timeout=30)
            r.raise_for_status()
            return True
        except Exception as exc:
            self.error_message = f"No se pudo crear el New Quiz: {exc}"
            logger.error(self.error_message, exc_info=True)
            return False

    # ------------------- New Quizzes: crear ítems tipo test -------------- #
    def _as_html_p(self, text: str) -> str:
        text = (text or "").strip()
        return f"<p>{text}</p>"

    def _uuid(self) -> str:
        return str(uuid.uuid4())

    def _build_choice_item(self, q: dict, position: int, default_points: float = 1.0) -> dict:
        """
        Transforma una pregunta de entrada sencilla a la forma requerida por New Quizzes (choice).
        Entrada esperada (flexible):
          {
            "question": "Texto de la pregunta",
            "choices": ["A", "B", "C", "D"],
            "correct": 1,                 # índice (0-based) o letra 'A'..'D' o el propio texto
            "points": 1.0,                # opcional
            "feedback_correct": "...",    # opcional (rich content admitido)
            "feedback_incorrect": "...",  # opcional
            "answer_feedback": {"B": "..."}  # opcional, por opción
          }
        """
        title = q.get("title") or f"Pregunta {position}"
        body = self._as_html_p(q.get("question", ""))

        # Crear choices con UUID
        raw_choices = q.get("choices", [])
        choices = []
        letter_map = {}  # 'A' -> uuid, 'B' -> uuid...
        for i, txt in enumerate(raw_choices, start=1):
            cid = self._uuid()
            choices.append({
                "id": cid,
                "position": i,
                "itemBody": self._as_html_p(str(txt)),
            })
            letter_map[chr(64 + i)] = cid  # A,B,C,...

        # Resolver la correcta -> UUID
        correct = q.get("correct")
        correct_uuid = None
        if isinstance(correct, int):
            # índice 0-based
            idx = max(0, min(len(choices) - 1, correct))
            correct_uuid = choices[idx]["id"] if choices else None
        elif isinstance(correct, str):
            # letra ('A', 'b', ...) o texto exacto de la opción
            c = correct.strip()
            if c.upper() in letter_map:
                correct_uuid = letter_map[c.upper()]
            else:
                # buscar por texto
                for ch in choices:
                    # quitar <p>...</p> para comparar
                    plain = re.sub(r"<\/?p>", "", ch["itemBody"], flags=re.I).strip()
                    if plain == c:
                        correct_uuid = ch["id"]
                        break

        points = float(q.get("points", default_points) or default_points)

        # Feedback por pregunta (correcto/incorrecto)
        feedback = {}
        if q.get("feedback_correct"):
            feedback["correct"] = self._as_html_p(q["feedback_correct"])
        if q.get("feedback_incorrect"):
            feedback["incorrect"] = self._as_html_p(q["feedback_incorrect"])

        # Feedback por respuesta (mapear a UUID -> html)
        answer_feedback_in = q.get("answer_feedback", {}) or {}
        answer_feedback = {}
        for key, fb in answer_feedback_in.items():
            # key puede ser letra, índice o texto
            target_uuid = None
            if isinstance(key, int):
                if 0 <= key < len(choices):
                    target_uuid = choices[key]["id"]
            elif isinstance(key, str):
                if key.upper() in letter_map:
                    target_uuid = letter_map[key.upper()]
                else:
                    # por texto
                    for ch in choices:
                        plain = re.sub(r"<\/?p>", "", ch["itemBody"], flags=re.I).strip()
                        if plain == key.strip():
                            target_uuid = ch["id"]
                            break
            if target_uuid:
                answer_feedback[target_uuid] = self._as_html_p(str(fb))

        # Construir payload conforme a la doc oficial (choice)
        return {
            "item": {
                "entry_type": "Item",
                "points_possible": points,
                "position": position,
                "entry": {
                    "interaction_type_slug": "choice",
                    "title": title,
                    "item_body": body,
                    "calculator_type": "none",
                    "interaction_data": {
                        "choices": choices
                    },
                    "properties": {
                        "shuffleRules": {
                            "choices": {"toLock": [], "shuffled": True}
                        },
                        "varyPointsByAnswer": False
                    },
                    "scoring_data": {
                        "value": correct_uuid
                    },
                    "scoring_algorithm": "Equivalence",
                    # 'feedback' y 'answer_feedback' son opcionales
                    **({"feedback": feedback} if feedback else {}),
                    **({"answer_feedback": answer_feedback} if answer_feedback else {}),
                }
            }
        }

    def create_new_quiz_and_items(self, course_id: int, settings: dict, items: list[dict]) -> bool:
        """
        Crea un New Quiz y a continuación añade ítems tipo 'choice' (uno por POST).
        'items' es una lista de dicts como los que espera _build_choice_item.
        """
        try:
            # 1) Crear el New Quiz
            url_quiz = f"{self._nq_base(course_id)}/quizzes"
            payload_quiz = {"quiz": {
                "title": settings.get("title", ""),
                "instructions": settings.get("description", ""),
                "published": settings.get("published", False),
            }}
            r = requests.post(url_quiz, headers=self._auth_headers(), json=payload_quiz, timeout=30)
            r.raise_for_status()
            quiz_obj = r.json() or {}
            # En New Quizzes, el 'id' que devuelve es el assignment_id usable en /items
            assignment_id = quiz_obj.get("id")
            if not assignment_id:
                self.error_message = "La API no devolvió un id para el New Quiz."
                return False

            # 2) Añadir cada ítem
            url_items = f"{self._nq_base(course_id)}/quizzes/{assignment_id}/items"
            for pos, q in enumerate(items, start=1):
                item_payload = self._build_choice_item(q, position=pos)
                r_item = requests.post(url_items, headers=self._auth_headers(),
                                       json=item_payload, timeout=30)
                r_item.raise_for_status()

            return True

        except Exception as exc:
            self.error_message = f"No se pudieron crear los ítems del New Quiz: {exc}"
            logger.error(self.error_message, exc_info=True)
            return False
