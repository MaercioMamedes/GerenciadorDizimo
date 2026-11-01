"""Handlers de listagem e detalhes de usuários."""

import uuid
from datetime import date, datetime

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.controllers.deps import require_admin_view
from app.core.templates import templates
from app.db.session import get_db
from app.models.paroquia import Paroquia
from app.models.perfil_dizimista import PerfilDizimista, StatusCadastro
from app.models.usuario import PerfilUsuario, Usuario
from app.services.usuario_query_service import listar_usuarios_paginado


def _normalizar_texto(valor: str | None) -> str | None:
    """Converte string vazia ou composta apenas de espaços em None."""
    if valor is None:
        return None
    limpo = valor.strip()
    return limpo if limpo else None


def _converter_ativo(valor: str | None) -> bool | None:
    """Converte string 'true'/'false' em booleano; string vazia = None."""
    limpo = _normalizar_texto(valor)
    if limpo is None:
        return None
    return limpo.lower() in {"true", "1", "on", "yes"}


def _converter_data(valor: str | None) -> date | None:
    """Converte string 'YYYY-MM-DD' em date; inválido/vazio = None."""
    limpo = _normalizar_texto(valor)
    if limpo is None:
        return None
    try:
        return datetime.strptime(limpo, "%Y-%m-%d").date()
    except ValueError:
        return None


async def listar_usuarios_view(
    request: Request,
    pagina: int = 1,
    tamanho_pagina: int = 10,
    perfil: str | None = None,
    ativo: str | None = None,
    status_cadastro: str | None = None,
    busca: str | None = None,
    numero_registro: str | None = None,
    data_nascimento: str | None = None,
    usuario_atual=Depends(require_admin_view),
    db: AsyncSession = Depends(get_db),
):
    # Normaliza parâmetros textuais
    busca_limpa = _normalizar_texto(busca)
    numero_registro_limpo = _normalizar_texto(numero_registro)
    perfil_limpo = _normalizar_texto(perfil)
    status_cadastro_limpo = _normalizar_texto(status_cadastro)

    # Converte tipos fortes de forma segura
    ativo_bool = _converter_ativo(ativo)
    data_nasc = _converter_data(data_nascimento)

    perfil_enum: PerfilUsuario | None = None
    if perfil_limpo:
        try:
            perfil_enum = PerfilUsuario(perfil_limpo)
        except ValueError:
            perfil_enum = None

    status_enum: StatusCadastro | None = None
    if status_cadastro_limpo:
        try:
            status_enum = StatusCadastro(status_cadastro_limpo)
        except ValueError:
            status_enum = None

    # numero_registro precisa ser int para comparar com a coluna do banco
    numero_registro_int: int | None = None
    if numero_registro_limpo:
        try:
            numero_registro_int = int(numero_registro_limpo)
        except ValueError:
            numero_registro_int = None

    resultado = await listar_usuarios_paginado(
        db,
        pagina=pagina,
        tamanho_pagina=tamanho_pagina,
        perfil=perfil_enum,
        ativo=ativo_bool,
        status_cadastro=status_enum,
        busca=busca_limpa,
        numero_registro=numero_registro_int,
        data_nascimento=data_nasc,
    )

    return templates.TemplateResponse(
        request,
        "usuarios/lista.html",
        {
            "usuario_atual": usuario_atual,
            "perfil_filtro": perfil_limpo or "",
            "ativo_filtro": ativo_bool,
            "status_cadastro_filtro": status_cadastro_limpo or "",
            "busca_filtro": busca_limpa or "",
            "numero_registro_filtro": numero_registro_limpo or "",
            "data_nascimento_filtro": data_nasc.isoformat() if data_nasc else "",
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
