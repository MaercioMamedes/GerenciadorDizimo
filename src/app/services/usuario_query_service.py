"""Serviço de consulta (query) para usuários.

Concentra a leitura e paginação da listagem de usuários,
separando a lógica de filtros da camada de apresentação.
"""

import math

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.usuario import PerfilUsuario, Usuario


async def listar_usuarios_paginado(
    db: AsyncSession,
    pagina: int = 1,
    tamanho_pagina: int = 10,
    perfil: PerfilUsuario | None = None,
) -> dict:
    """Retorna a lista paginada de usuários não excluídos.

    O filtro por perfil ``DIZIMISTA`` considera tanto usuários cujo
    ``Usuario.perfil`` seja ``DIZIMISTA`` quanto administradores que
    também possuam um perfil de dizimista vinculado.
    """
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
