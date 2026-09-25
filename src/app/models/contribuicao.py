import uuid
from typing import TYPE_CHECKING
from app.models.base import utc_now
from datetime import date, datetime
from sqlalchemy import Numeric, Date, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.perfil_dizimista import PerfilDizimista
    from app.models.igreja import Igreja

class Contribuicao(Base, TimestampMixin):
    __tablename__ = "contribuicao"
    __table_args__ = (
        UniqueConstraint("perfil_dizimista_id", "mes_referencia", name="uq_contribuicao_dizimista_mes"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    perfil_dizimista_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("perfil_dizimista.id"), nullable=False
    )
    igreja_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("igreja.id"), nullable=False
    )
    mes_referencia: Mapped[date] = mapped_column(Date, nullable=False)
    valor: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    data_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    perfil_dizimista: Mapped["PerfilDizimista"] = relationship()
    igreja: Mapped["Igreja"] = relationship()
