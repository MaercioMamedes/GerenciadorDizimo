import uuid
from app.models.base import utc_now
from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class SecurityLog(Base):
    __tablename__ = "security_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Sem ForeignKey intencionalmente: logs devem persistir mesmo se o usuário for excluído
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    evento: Mapped[str] = mapped_column(String(50), nullable=False)  # login_sucesso, login_falha, logout, bloqueio
    ip_origem: Mapped[str | None] = mapped_column(String(45), nullable=True)
    detalhes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    executado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
