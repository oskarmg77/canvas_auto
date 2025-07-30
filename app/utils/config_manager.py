# app/utils/config_manager.py

import json
import os

# Definimos una ruta consistente para el archivo de configuración
CONFIG_FILE = "config.json"


def save_credentials(url: str, token: str):
    """Guarda la URL y el token en el archivo de configuración."""
    credentials = {
        "canvas_url": url,
        "api_token": token
    }
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(credentials, f, indent=4)
        return True
    except IOError as e:
        print(f"Error al guardar el archivo de configuración: {e}")
        return False


def load_credentials():
    """Carga la URL y el token desde el archivo de configuración."""
    if not os.path.exists(CONFIG_FILE):
        return None

    try:
        with open(CONFIG_FILE, 'r') as f:
            credentials = json.load(f)
            if "canvas_url" in credentials and "api_token" in credentials:
                return credentials
            else:
                return None
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error al leer o procesar el archivo de configuración: {e}")
        return None