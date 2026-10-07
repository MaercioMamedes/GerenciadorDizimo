"""Instância única e centralizada do Jinja2Templates, evitando caminhos divergentes."""
from pathlib import Path

from fastapi.templating import Jinja2Templates

# src/app/core/templates.py -> sobe 2 níveis até src/app/ -> entra em templates/
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
