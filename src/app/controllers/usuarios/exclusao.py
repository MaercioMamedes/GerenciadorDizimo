"""Handler de exclusão de usuários."""

import uuid

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.controllers.deps import get_usuario_atual_opcional
from app.controllers.usuarios.helpers import eh_administrador
from app.db.session import get_db
from app.models.perfil_dizimista import PerfilDizimista
from app.models.usuario import Usuario
from app.services.usuario_service import excluir_usuario


async def excluir_usuario_via_formulario(
    request: Request,
    usuario_id: uuid.UUID,
    usuario_atual=Depends(get_usuario_atual_opcional),
    db: AsyncSession = Depends(get_db),
):
    if usuario_atual is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="É necessário estar autenticado.",
        )

    if not eh_administrador(usuario_atual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para excluir este usuário.",
        )

    stmt = (
        select(Usuario)
        .where(Usuario.id == usuario_id)
        .options(selectinload(Usuario.perfil_dizimista))
    )
    resultado = await db.execute(stmt)
    usuario = resultado.scalar_one_or_none()

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado."
        )

    await excluir_usuario(db, usuario)

    return RedirectResponse(url="/usuarios", status_code=status.HTTP_303_SEE_OTHER)
