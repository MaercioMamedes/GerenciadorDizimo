import uuid
from app.models.base import utc_now
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class Notificacao(Base):
    __tablename__ = "notificacao"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuario.id"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)  # aprovacao_cadastro, rejeicao_cadastro
    mensagem: Mapped[str] = mapped_column(String(500), nullable=False)
    lida: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enviada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
