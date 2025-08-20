import os
import io
import fitz  # PyMuPDF
from PIL import Image
from app.utils.logger_config import logger
from app.api.canvas_client import CanvasClient


def _get_attachments_from_submission(submission):
    """Extrae la lista de adjuntos de una entrega, incluyendo el historial."""
    attachments = submission.get('attachments', [])

    # Como fallback, revisa el historial de entregas si no hay adjuntos directos
    if not attachments and submission.get('submission_history'):
        latest_submission = submission['submission_history'][-1]
        attachments = latest_submission.get('attachments', [])

    return attachments


def _download_and_save_attachment(attachment, dir_path, canvas_api: CanvasClient):
    """Descarga un adjunto, lo guarda localmente y devuelve su contenido."""
    file_url = attachment.get('url')
    file_name = attachment.get('filename', 'archivo_desconocido')
    file_path = os.path.join(dir_path, file_name)

    if not file_url:
        logger.warning(f"El adjunto '{file_name}' no tiene URL para descargar.")
        return None, None

    try:
        # Usar la sesión del cliente de Canvas para mantener la autenticación
        response = canvas_api.session.get(file_url, stream=True)
        response.raise_for_status()

        # Guardar el archivo localmente
        os.makedirs(dir_path, exist_ok=True)
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info(f"Archivo '{file_name}' descargado en '{file_path}'.")
        return response.content, attachment.get('content-type')

    except Exception as e:
        logger.error(f"Error al descargar o guardar el archivo '{file_name}' desde {file_url}: {e}")
        return None, None


def extract_submission_content(submission: dict, base_path: str, course_name: str, assignment_name: str, user_name: str, canvas_api: CanvasClient) -> list:
    """
    Extrae el contenido de los adjuntos de una entrega (texto y/o imágenes).
    Soporta archivos PDF, de texto plano e imágenes.

    Args:
        submission (dict): El objeto de la entrega de la API de Canvas.
        base_path (str): Directorio base para guardar los archivos.
        course_name (str): Nombre del curso.
        assignment_name (str): Nombre de la actividad.
        user_name (str): Nombre del estudiante.
        canvas_api (CanvasClient): Cliente de la API de Canvas para realizar descargas.

    Returns:
        list: Una lista que contiene strings (para el texto) y objetos PIL.Image.
    """
    content_parts = []

    # Limpiar nombres para la ruta del directorio
    safe_course_name = "".join(c for c in course_name if c.isalnum() or c in (' ', '_')).rstrip()
    safe_assignment_name = "".join(c for c in assignment_name if c.isalnum() or c in (' ', '_')).rstrip()
    safe_user_name = "".join(c for c in user_name if c.isalnum() or c in (' ', '_')).rstrip()

    # Directorio específico para los archivos de este usuario
    user_files_dir = os.path.join(base_path, safe_course_name, safe_assignment_name, f"Archivos_{safe_user_name}")

    attachments = _get_attachments_from_submission(submission)
    if not attachments:
        logger.warning(f"No se encontraron adjuntos para el usuario '{user_name}'.")
        if submission.get('body'):
            content_parts.append(f"Contenido del cuerpo de la entrega:\n{submission['body']}\n")
        return content_parts

    for attachment in attachments:
        file_content, content_type = _download_and_save_attachment(attachment, user_files_dir, canvas_api)

        if not file_content:
            continue

        try:
            if content_type == 'application/pdf':
                pdf_document = fitz.open(stream=io.BytesIO(file_content), filetype="pdf")
                for page in pdf_document:
                    content_parts.append(page.get_text())
                    for img in page.get_images(full=True):
                        xref = img[0]
                        base_image = pdf_document.extract_image(xref)
                        content_parts.append(Image.open(io.BytesIO(base_image["image"])))
            elif content_type and content_type.startswith('image/'):
                content_parts.append(Image.open(io.BytesIO(file_content)))
            elif content_type and content_type.startswith('text/'):
                content_parts.append(file_content.decode('utf-8', errors='ignore'))
            else:
                logger.warning(f"Tipo de archivo no soportado '{content_type}' para '{attachment.get('filename')}'.")
        except Exception as e:
            logger.error(f"Error al procesar el contenido de '{attachment.get('filename')}': {e}")

    if submission.get('body'):
        content_parts.insert(0, f"Contenido del cuerpo de la entrega:\n{submission['body']}\n")

    return content_parts