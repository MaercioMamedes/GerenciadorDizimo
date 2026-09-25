import uuid
from typing import TYPE_CHECKING
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.igreja import Igreja

class Paroquia(Base, TimestampMixin):
    __tablename__ = "paroquia"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    cnpj: Mapped[str | None] = mapped_column(String(18), unique=True, nullable=True)
    endereco: Mapped[str | None] = mapped_column(String(255), nullable=True)

    igrejas: Mapped[list["Igreja"]] = relationship(back_populates="paroquia")

    def __repr__(self):
        return f"Paroquia(id={self.id}, nome={self.nome}, cnpj={self.cnpj}, endereco={self.endereco})"