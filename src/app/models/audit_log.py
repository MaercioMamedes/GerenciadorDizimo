import uuid
from datetime import datetime
from app.models.base import utc_now
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tabela: Mapped[str] = mapped_column(String(100), nullable=False)
    operacao: Mapped[str] = mapped_column(String(20), nullable=False)  # INSERT/UPDATE/DELETE
    registro_id: Mapped[str] = mapped_column(String(100), nullable=False)
    dados_anteriores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    dados_novos: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
# Sem ForeignKey intencionalmente: logs devem persistir mesmo se o usuário for excluído
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    executado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    def __repr__(self):
        return f"AuditLog(id={self.id}, tabela={self.tabela}, operacao={self.operacao}, " \
               f"registro_id={self.registro_id}, dados_anteriores={self.dados_anteriores}, " \
               f"dados_novos={self.dados_novos}, executado_em={self.executado_em})"