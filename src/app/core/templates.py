"""Configuração centralizada dos templates Jinja2."""

from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.core.template_filters import format_date, format_dt

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Registra filtros de data/timezone globalmente
templates.env.filters["format_dt"] = format_dt
templates.env.filters["format_date"] = format_date
