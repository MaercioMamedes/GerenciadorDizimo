import uuid
from app.models.base import utc_now
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class ConsentimentoLgpd(Base):
    __tablename__ = "consentimento_lgpd"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuario.id"), nullable=False, unique=True
    )
    aceito: Mapped[bool] = mapped_column(Boolean, nullable=False)
    versao_termo: Mapped[str] = mapped_column(String(10), nullable=False, default="1.0")
    aceito_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
