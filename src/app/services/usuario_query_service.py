"""Serviço de consulta (query) para usuários.

Concentra a leitura e paginação da listagem de usuários,
separando a lógica de filtros da camada de apresentação.
"""

import math
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.perfil_dizimista import PerfilDizimista, StatusCadastro
from app.models.usuario import PerfilUsuario, Usuario


async def listar_usuarios_paginado(
    db: AsyncSession,
    pagina: int = 1,
    tamanho_pagina: int = 10,
    perfil: PerfilUsuario | None = None,
    busca: str | None = None,
    numero_registro: int | None = None,
    data_nascimento: date | None = None,
    ativo: bool | None = None,
    status_cadastro: StatusCadastro | None = None,
) -> dict:
    """Retorna a lista paginada de usuários não excluídos.

    Filtros suportados:
      - ``perfil``: ``DIZIMISTA`` considera também administradores com perfil
        de dizimista vinculado; ``ADMINISTRADOR`` filtra apenas administradores.
      - ``busca``: busca parcial case-insensitive no nome do usuário.
      - ``numero_registro``: filtro exato pelo número de registro do dizimista.
      - ``data_nascimento``: filtro exato pela data de nascimento.
      - ``ativo``: filtro pelo campo ``Usuario.ativo``.
      - ``status_cadastro``: filtro pelo status do perfil de dizimista.
    """

    if perfil is not None and not isinstance(perfil, PerfilUsuario):
        return {
            "itens": [],
            "pagina": max(pagina, 1),
            "tamanho_pagina": max(min(tamanho_pagina, 100), 1),
            "total_registros": 0,
            "total_paginas": 1,
        }

    pagina = max(pagina, 1)

    tamanho_pagina = max(min(tamanho_pagina, 100), 1)

    filtro = [Usuario.excluido_em.is_(None)]

    if perfil == PerfilUsuario.DIZIMISTA:
        filtro.append(
            or_(
                Usuario.perfil == PerfilUsuario.DIZIMISTA,
                Usuario.perfil_dizimista.has(),
            )
        )
    elif perfil == PerfilUsuario.ADMINISTRADOR:
        filtro.append(Usuario.perfil == PerfilUsuario.ADMINISTRADOR)

    if busca:
        filtro.append(Usuario.nome.ilike(f"%{busca}%"))

    if numero_registro is not None:
        filtro.append(
            Usuario.perfil_dizimista.has(
                PerfilDizimista.numero_registro == numero_registro
            )
        )

    if data_nascimento is not None:
        filtro.append(Usuario.data_nascimento == data_nascimento)

    if ativo is not None:
        filtro.append(Usuario.ativo.is_(ativo))

    if status_cadastro is not None:
        filtro.append(
            Usuario.perfil_dizimista.has(
                PerfilDizimista.status_cadastro == status_cadastro
            )
        )

    total_registros = (
        await db.execute(select(func.count()).select_from(Usuario).where(*filtro))
    ).scalar_one()

    total_paginas = max(math.ceil(total_registros / tamanho_pagina), 1)
    pagina = min(pagina, total_paginas)

    resultado = await db.execute(
        select(Usuario)
        .where(*filtro)
        .options(selectinload(Usuario.perfil_dizimista))
        .order_by(Usuario.nome)
        .offset((pagina - 1) * tamanho_pagina)
        .limit(tamanho_pagina)
    )
    itens = resultado.scalars().all()

    return {
        "itens": itens,
        "pagina": pagina,
        "tamanho_pagina": tamanho_pagina,
        "total_registros": total_registros,
        "total_paginas": total_paginas,
    }
