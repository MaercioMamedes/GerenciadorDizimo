"""Funções auxiliares compartilhadas pelos handlers de usuários."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.paroquia import Paroquia
from app.models.perfil_dizimista import PerfilDizimista, StatusCadastro
from app.models.usuario import PerfilUsuario, Usuario
from app.services.usuario_service import PerfilDizimistaPayload


def eh_administrador(usuario_atual) -> bool:
    """Verifica se o usuário autenticado é administrador."""
    return (
        usuario_atual is not None
        and usuario_atual.perfil == PerfilUsuario.ADMINISTRADOR
    )


def perfil_e_dizimista(perfil: PerfilUsuario, tambem_dizimista: bool) -> bool:
    """Determina se o usuário em questão possui perfil de dizimista."""
    return (perfil == PerfilUsuario.DIZIMISTA) or (
        perfil == PerfilUsuario.ADMINISTRADOR and tambem_dizimista
    )


def montar_payload_perfil_dizimista(
    eh_dizimista: bool,
    igreja_id: str | None,
    numero_registro: int | None,
    endereco: str | None,
    bairro: str | None,
    cidade: str | None,
    status_cadastro: str | None,
) -> PerfilDizimistaPayload | None:
    """Monta o payload do perfil dizimista quando aplicável."""
    if not eh_dizimista or not igreja_id:
        return None

    return PerfilDizimistaPayload(
        igreja_id=uuid.UUID(igreja_id),
        numero_registro=numero_registro,
        endereco=endereco,
        bairro=bairro,
        cidade=cidade,
        status_cadastro=StatusCadastro(status_cadastro)
        if status_cadastro
        else StatusCadastro.PENDENTE,
    )


async def buscar_usuario_com_relacionamentos(
    db: AsyncSession, usuario_id: uuid.UUID
) -> Usuario:
    """Busca o usuário com paróquia e perfil de dizimista carregados."""
    stmt = (
        select(Usuario)
        .where(Usuario.id == usuario_id)
        .options(
            selectinload(Usuario.paroquia).selectinload(Paroquia.igrejas),
            selectinload(Usuario.perfil_dizimista),
        )
    )
    resultado = await db.execute(stmt)
    usuario = resultado.scalar_one_or_none()

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado."
        )

    return usuario
