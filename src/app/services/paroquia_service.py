# app/services/paroquia_service.py
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.igreja import Igreja
from app.models.paroquia import Paroquia
from app.schemas.paroquia import ParoquiaCreate, ParoquiaUpdate


class ParoquiaNaoEncontrada(Exception):
    pass


async def listar_paroquias(db: AsyncSession) -> list[Paroquia]:
    resultado = await db.execute(
        select(Paroquia)
        .outerjoin(
            Igreja,
            (Igreja.paroquia_id == Paroquia.id) & (Igreja.is_matriz.is_(True)),
        )
        .options(selectinload(Paroquia.igrejas))
        .order_by(Igreja.nome)
    )
    return list(resultado.scalars().unique().all())


async def obter_paroquia(db: AsyncSession, paroquia_id: uuid.UUID) -> Paroquia:
    resultado = await db.execute(
        select(Paroquia)
        .options(selectinload(Paroquia.igrejas))
        .where(Paroquia.id == paroquia_id)
    )
    paroquia = resultado.scalar_one_or_none()
    if not paroquia:
        raise ParoquiaNaoEncontrada(f"Paróquia {paroquia_id} não encontrada.")
    return paroquia


async def criar_paroquia(db: AsyncSession, dados: ParoquiaCreate) -> Paroquia:
    paroquia = Paroquia(cnpj=dados.cnpj)
    db.add(paroquia)
    await db.flush()  # garante paroquia.id antes de criar a igreja

    igreja_matriz = Igreja(
        nome=dados.nome_matriz,
        endereco=dados.endereco_matriz,
        is_matriz=True,
        paroquia_id=paroquia.id,
    )
    db.add(igreja_matriz)

    await db.commit()
    await db.refresh(paroquia, attribute_names=["igrejas"])
    return paroquia


async def atualizar_paroquia(
    db: AsyncSession, paroquia_id: uuid.UUID, dados: ParoquiaUpdate
) -> Paroquia:
    paroquia = await obter_paroquia(db, paroquia_id)
    for campo, valor in dados.model_dump().items():
        setattr(paroquia, campo, valor)
    await db.commit()
    await db.refresh(paroquia)
    return paroquia
