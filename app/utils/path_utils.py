from pathlib import Path
import sys

def resource_path(rel_path: str | Path) -> Path:
    """
    Devuelve la ruta real a un recurso dentro del bundle (PyInstaller)
    o del repo (desarrollo).
    """
    try:
        base = Path(getattr(sys, "_MEIPASS"))  # cuando es .exe onefile
    except Exception:
        base = Path(__file__).resolve().parents[2]  # raíz del repo en dev
    return (base / rel_path).resolve()
