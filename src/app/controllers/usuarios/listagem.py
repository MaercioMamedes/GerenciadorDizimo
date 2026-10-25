"""Handlers de listagem e detalhes de usuários."""

import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.controllers.deps import require_admin_view
from app.core.templates import templates
from app.db.session import get_db
from app.models.paroquia import Paroquia
from app.models.perfil_dizimista import PerfilDizimista
from app.models.usuario import PerfilUsuario, Usuario
from app.services.usuario_query_service import listar_usuarios_paginado


async def listar_usuarios_view(
    request: Request,
    pagina: int = 1,
    tamanho_pagina: int = 10,
    perfil: str | None = None,
    usuario_atual=Depends(require_admin_view),
    db: AsyncSession = Depends(get_db),
):
    perfil_enum: PerfilUsuario | None = None
    if perfil:
        try:
            perfil_enum = PerfilUsuario(perfil)
        except ValueError:
            perfil_enum = None

    resultado = await listar_usuarios_paginado(
        db, pagina=pagina, tamanho_pagina=tamanho_pagina, perfil=perfil_enum
    )

    return templates.TemplateResponse(
        request,
        "usuarios/lista.html",
        {
            "usuario_atual": usuario_atual,
            "perfil_filtro": perfil_enum.value if perfil_enum else "",
            **resultado,
        },
    )


async def detalhes_usuario_view(
    request: Request,
    usuario_id: uuid.UUID,
    usuario_atual=Depends(require_admin_view),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Usuario)
        .where(Usuario.id == usuario_id)
        .options(
            selectinload(Usuario.paroquia).selectinload(Paroquia.igrejas),
            selectinload(Usuario.perfil_dizimista).selectinload(PerfilDizimista.igreja),
        )
    )
    resultado = await db.execute(stmt)
    usuario = resultado.scalar_one_or_none()

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado."
        )

    return templates.TemplateResponse(
        request,
        "usuarios/detalhes.html",
        {
            "usuario_atual": usuario_atual,
            "usuario": usuario,
        },
    )
