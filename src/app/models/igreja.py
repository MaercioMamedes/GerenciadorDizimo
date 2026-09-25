import uuid
from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.paroquia import Paroquia
    
class Igreja(Base, TimestampMixin):
    __tablename__ = "igreja"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    is_matriz: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    endereco: Mapped[str | None] = mapped_column(String(255), nullable=True)

    paroquia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("paroquia.id"), nullable=False
    )
    paroquia: Mapped["Paroquia"] = relationship(back_populates="igrejas")

    def __repr__(self):
        return f"Igreja(id={self.id}, nome={self.nome}, is_matriz={self.is_matriz}, endereco={self.endereco})"