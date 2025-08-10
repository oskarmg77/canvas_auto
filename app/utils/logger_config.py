import logging
import sys

# Crea el logger principal
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Formato para los mensajes
formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Handler para consola
console_handler = logging.StreamHandler(sys.stdout)

# Forzar UTF-8 en consola para que acepte ✔, ✖ y otros símbolos
try:
    console_handler.stream.reconfigure(encoding='utf-8')
except AttributeError:
    import io
    console_handler.stream = io.TextIOWrapper(
        sys.stdout.buffer, encoding='utf-8', errors='replace'
    )

console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
