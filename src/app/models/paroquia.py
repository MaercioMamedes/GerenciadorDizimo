import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.igreja import Igreja


class Paroquia(Base, TimestampMixin):
    __tablename__ = "paroquia"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cnpj: Mapped[str | None] = mapped_column(String(18), unique=True, nullable=True)

    igrejas: Mapped[list["Igreja"]] = relationship(back_populates="paroquia")

    @property
    def matriz(self) -> "Igreja | None":
        """Retorna a igreja matriz vinculada a esta paróquia, se existir."""
        return next((igreja for igreja in self.igrejas if igreja.is_matriz), None)

    @property
    def nome(self) -> str | None:
        """Nome da paróquia = nome da igreja matriz (campo exclusivo removido)."""
        matriz = self.matriz
        return matriz.nome if matriz else None

    @property
    def endereco(self) -> str | None:
        """Endereço da paróquia = endereço da igreja matriz."""
        matriz = self.matriz
        return matriz.endereco if matriz else None

    def __repr__(self):
        return f"Paroquia(id={self.id}, cnpj={self.cnpj}, nome={self.nome})"
