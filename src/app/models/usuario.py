import uuid
from datetime import date
from typing import TYPE_CHECKING
import enum
from sqlalchemy import String, Enum, ForeignKey, Boolean, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.paroquia import Paroquia
    from app.models.perfil_dizimista import PerfilDizimista

class PerfilUsuario(str, enum.Enum):
    ADMINISTRADOR = "administrador"
    DIZIMISTA = "dizimista"


class Usuario(Base, TimestampMixin):
    __tablename__ = "usuario"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    telefone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    data_nascimento: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Controla exclusivamente PERMISSÕES de acesso ao sistema (RBAC)
    perfil: Mapped[PerfilUsuario] = mapped_column(
        Enum(PerfilUsuario, name="perfil_usuario_enum"), nullable=False
    )

    # Preenchido somente quando perfil == ADMINISTRADOR
    paroquia_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("paroquia.id"), nullable=True
    )

    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    paroquia: Mapped["Paroquia | None"] = relationship()
    perfil_dizimista: Mapped["PerfilDizimista | None"] = relationship(
        back_populates="usuario", uselist=False
    )

    def __repr__(self):
        return f"Usuario(id={self.id}, nome={self.nome}, perfil={self.perfil})"
