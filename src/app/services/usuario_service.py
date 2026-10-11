import math

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_senha
from app.models.usuario import PerfilUsuario, Usuario
from app.schemas.usuario import UsuarioCreate


async def criar_usuario(db: AsyncSession, dados: UsuarioCreate) -> Usuario:
    """Cria um novo usuário, garantindo unicidade de e-mail e hash de senha."""
    resultado = await db.execute(select(Usuario).where(Usuario.email == dados.email))
    if resultado.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um usuário cadastrado com este e-mail.",
        )

    usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        senha_hash=hash_senha(dados.senha),
        telefone=dados.telefone,
        data_nascimento=dados.data_nascimento,
        perfil=dados.perfil,
        paroquia_id=dados.paroquia_id,
    )

    db.add(usuario)
    await db.commit()
    await db.refresh(usuario)
    return usuario


async def listar_usuarios_paginado(
    db: AsyncSession,
    pagina: int = 1,
    tamanho_pagina: int = 10,
    perfil: PerfilUsuario | None = None,
) -> dict:
    """
    Retorna uma página de usuários ordenados por nome, junto com
    metadados de paginação.

    Args:
        pagina: número da página (1-indexed).
        tamanho_pagina: quantidade de registros por página.
        perfil: filtro opcional por perfil (administrador/dizimista).

    Returns:
        dict com: itens, pagina, tamanho_pagina, total_registros, total_paginas
    """
    pagina = max(pagina, 1)
    tamanho_pagina = max(min(tamanho_pagina, 100), 1)  # limite de segurança

    filtro = []
    if perfil is not None:
        filtro.append(Usuario.perfil == perfil)

    total_registros = (
        await db.execute(select(func.count()).select_from(Usuario).where(*filtro))
    ).scalar_one()

    total_paginas = max(math.ceil(total_registros / tamanho_pagina), 1)
    pagina = min(pagina, total_paginas)

    resultado = await db.execute(
        select(Usuario)
        .where(*filtro)
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
