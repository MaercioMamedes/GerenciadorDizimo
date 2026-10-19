import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.perfil_dizimista import PerfilDizimista


async def sugerir_numero_registro(db: AsyncSession) -> int:
    """Retorna o próximo número de registro disponível (máximo + 1).

    Considera números já migrados de registros manuais antigos,
    evitando conflito com novos dizimistas.
    """
    resultado = await db.execute(select(func.max(PerfilDizimista.numero_registro)))
    maximo = resultado.scalar_one_or_none()
    return (maximo or 0) + 1


async def validar_numero_registro_unico(
    db: AsyncSession,
    numero_registro: int | None,
    perfil_id: uuid.UUID | None = None,
) -> None:
    """Garante que o número de registro, quando informado, seja único.

    Args:
        db: sessão assíncrona do banco.
        numero_registro: número a ser validado.
        perfil_id: identificador do perfil atual, usado em atualizações
            para não conflitar consigo mesmo.
    """
    if numero_registro is None:
        return

    stmt = select(PerfilDizimista).where(
        PerfilDizimista.numero_registro == numero_registro
    )
    if perfil_id:
        stmt = stmt.where(PerfilDizimista.id != perfil_id)

    existente = (await db.execute(stmt)).scalar_one_or_none()
    if existente is not None:
        raise ValueError(
            f"O número de registro {numero_registro} já está em uso por outro dizimista."
        )
