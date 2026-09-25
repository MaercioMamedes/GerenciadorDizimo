from datetime import datetime, timezone
from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    """Retorna datetime atual com timezone UTC explícito."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base declarativa para todos os modelos ORM."""
    pass


class TimestampMixin:
    """Mixin para colunas de auditoria temporal padrão."""
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now,
        onupdate=utc_now, nullable=False
    )
