from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.security import hash_senha
from app.models.usuario import Usuario
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
