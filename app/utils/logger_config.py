# app/utils/logger_config.py
from __future__ import annotations
import logging
import sys
import os
import io
from pathlib import Path

LOG_FILENAME = "canvas_auto.log"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

def _ensure_log_dir() -> Path:
    """
    Crea (si no existe) una carpeta 'logs' en el directorio de trabajo.
    Evita usar _MEIPASS (solo lectura) en ejecutables onefile.
    """
    try:
        base = Path.cwd()
        log_dir = base / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir
    except Exception:
        # Último recurso: carpeta actual
        return Path(".")

def _safe_stream(std) -> io.TextIOWrapper | None:
    """
    Devuelve un stream de texto UTF-8 si es posible.
    En .exe windowed, stdout/stderr suelen ser None → devuelve None.
    """
    if std is None:
        return None

    # Si soporta reconfigure (Py 3.7+), úsalo.
    try:
        if hasattr(std, "reconfigure"):
            std.reconfigure(encoding="utf-8", newline="")
            return std
    except Exception:
        pass

    # Si tiene buffer binario, envuélvelo en TextIOWrapper UTF-8.
    try:
        buf = getattr(std, "buffer", None)
        if buf is not None:
            return io.TextIOWrapper(buf, encoding="utf-8", errors="replace")
    except Exception:
        pass

    # Si nada de lo anterior, mejor no usar stream.
    return None

# Handlers
handlers: list[logging.Handler] = []

# Archivo siempre, en UTF-8
log_path = _ensure_log_dir() / LOG_FILENAME
file_handler = logging.FileHandler(log_path, encoding="utf-8")
handlers.append(file_handler)

# Consola solo si existe (en .exe windowed normalmente será None)
stdout_stream = _safe_stream(getattr(sys, "stdout", None))
if stdout_stream is not None:
    handlers.append(logging.StreamHandler(stdout_stream))

# Config global
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, handlers=handlers, force=True)

# Logger de la app
logger = logging.getLogger("canvas_auto")
logger.propagate = False
