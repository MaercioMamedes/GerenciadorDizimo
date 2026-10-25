"""Carregamento de dados auxiliares e renderização dos templates de usuários."""

from fastapi import Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.templates import templates
from app.models.igreja import Igreja
from app.models.paroquia import Paroquia
from app.models.usuario import Usuario


async def carregar_paroquias(db: AsyncSession) -> list[Paroquia]:
    """
    Retorna as paróquias com a relationship de igrejas carregada,
    necessária para que a property Paroquia.nome funcione no template.
    """
    resultado = await db.execute(
        select(Paroquia).options(selectinload(Paroquia.igrejas)).order_by(Paroquia.id)
    )
    return list(resultado.scalars().all())


async def carregar_igrejas(db: AsyncSession) -> list[Igreja]:
    return list(
        (await db.execute(select(Igreja).order_by(Igreja.nome))).scalars().all()
    )


def renderizar_formulario_usuario(
    request: Request,
    usuario_atual,
    usuario: Usuario | None,
    erros: list[str],
    paroquias: list[Paroquia],
    igrejas: list[Igreja],
    status_code: int = status.HTTP_200_OK,
):
    """Renderiza o template do formulário de criação/edição de usuários."""
    return templates.TemplateResponse(
        request,
        "usuarios/formulario.html",
        {
            "usuario_atual": usuario_atual,
            "usuario": usuario,
            "erros": erros,
            "paroquias": paroquias,
            "igrejas": igrejas,
        },
        status_code=status_code,
    )
