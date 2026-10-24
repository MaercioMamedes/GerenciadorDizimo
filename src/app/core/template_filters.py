"""Filtros Jinja2 para formatação de datas com timezone local."""

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

FUSO_LOCAL = ZoneInfo("America/Maceio")


def _as_local(value: datetime | None) -> datetime | None:
    """Converte um datetime UTC (ou naive) para o fuso local."""
    if value is None:
        return None

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(FUSO_LOCAL)


def format_dt(value: datetime | None, fmt: str = "%d/%m/%Y %H:%M") -> str:
    """Formata datetime no fuso local. Retorna '—' quando nulo."""
    local = _as_local(value)
    return local.strftime(fmt) if local else "—"


def format_date(value: date | None, fmt: str = "%d/%m/%Y") -> str:
    """Formata date ou datetime no fuso local. Retorna '—' quando nulo."""
    if value is None:
        return "—"

    # Se for datetime.date sem informação de hora, formata diretamente
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.strftime(fmt)

    return format_dt(value, fmt)
