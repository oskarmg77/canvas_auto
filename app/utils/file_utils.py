import os
import json
from app.utils.logger_config import logger

def save_evaluation(evaluation_data, user_name, base_path, course_name, assignment_name):
    """
    Guarda los datos de una evaluación en un archivo.

    Crea una estructura de directorios anidada para organizar las evaluaciones
    y guarda el contenido de la evaluación en un archivo de texto o JSON.

    Args:
        evaluation_data (dict or str): Los datos de la evaluación a guardar.
        user_name (str): El nombre del usuario/estudiante.
        base_path (str): El directorio base seleccionado por el usuario.
        course_name (str): El nombre del curso.
        assignment_name (str): El nombre de la actividad.
    """
    try:
        # Limpiar nombres para que sean válidos como nombres de directorio/archivo
        safe_course_name = "".join(c for c in course_name if c.isalnum() or c in (' ', '_')).rstrip()
        safe_assignment_name = "".join(c for c in assignment_name if c.isalnum() or c in (' ', '_')).rstrip()
        safe_user_name = "".join(c for c in user_name if c.isalnum() or c in (' ', '_')).rstrip()

        # Crear la ruta del directorio
        dir_path = os.path.join(base_path, safe_course_name, safe_assignment_name)
        os.makedirs(dir_path, exist_ok=True)

        # Crear el nombre del archivo
        file_name = f"Evaluacion_{safe_user_name}.txt"
        file_path = os.path.join(dir_path, file_name)

        # Guardar el contenido
        with open(file_path, 'w', encoding='utf-8') as f:
            if isinstance(evaluation_data, dict):
                json.dump(evaluation_data, f, ensure_ascii=False, indent=4)
            else:
                f.write(str(evaluation_data))
        
        logger.info(f"Evaluación guardada exitosamente en: {file_path}")

    except Exception as e:
        logger.error(f"Error al guardar la evaluación para {user_name} en {base_path}: {e}")