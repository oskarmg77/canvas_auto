# app/utils/logger_config.py

import logging
import os

def setup_logger():
    """
    Configura un logger para registrar eventos de la aplicación en un archivo.
    """
    # Crear el directorio de logs si no existe
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # Configuración básica del logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("logs/canvas_auto.log"), # Guarda los logs en un archivo
            logging.StreamHandler() # Muestra los logs en la consola
        ]
    )

    return logging.getLogger(__name__)

# Crear una única instancia del logger para ser importada por otros módulos
logger = setup_logger()