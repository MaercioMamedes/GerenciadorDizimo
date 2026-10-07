# app/services/paroquia_service.py
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paroquia import Paroquia
from app.schemas.paroquia import ParoquiaCreate, ParoquiaUpdate


class ParoquiaNaoEncontrada(Exception):
    pass


async def listar_paroquias(db: AsyncSession) -> list[Paroquia]:
    resultado = await db.execute(select(Paroquia).order_by(Paroquia.nome))
    return list(resultado.scalars().all())


async def obter_paroquia(db: AsyncSession, paroquia_id: uuid.UUID) -> Paroquia:
    paroquia = await db.get(Paroquia, paroquia_id)
    if not paroquia:
        raise ParoquiaNaoEncontrada(f"Paróquia {paroquia_id} não encontrada.")
    return paroquia


async def criar_paroquia(db: AsyncSession, dados: ParoquiaCreate) -> Paroquia:
    paroquia = Paroquia(**dados.model_dump())
    db.add(paroquia)
    await db.commit()
    await db.refresh(paroquia)
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
