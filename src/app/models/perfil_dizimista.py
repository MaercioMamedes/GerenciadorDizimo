import uuid
from typing import TYPE_CHECKING
import enum
from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.usuario import Usuario
    from app.models.igreja import Igreja

class StatusCadastro(str, enum.Enum):
    PENDENTE = "pendente"
    APROVADO = "aprovado"
    REJEITADO = "rejeitado"


class PerfilDizimista(Base, TimestampMixin):
    __tablename__ = "perfil_dizimista"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuario.id"), nullable=False, unique=True
    )
    igreja_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("igreja.id"), nullable=False
    )
    status_cadastro: Mapped[StatusCadastro] = mapped_column(
        Enum(StatusCadastro, name="status_cadastro_enum"),
        default=StatusCadastro.PENDENTE, nullable=False
    )

    # Endereço do dizimista
    endereco: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bairro: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cidade: Mapped[str | None] = mapped_column(String(100), nullable=True)

    usuario: Mapped["Usuario"] = relationship(back_populates="perfil_dizimista")
    igreja: Mapped["Igreja"] = relationship()

    def __repr__(self):
        return f"PerfilDizimista(id={self.id}, usuario_id={self.usuario_id}, status={self.status_cadastro})"

    def __str__(self):
        return f"PerfilDizimista(id={self.id}, usuario_id={self.usuario_id}, status={self.status_cadastro})"
