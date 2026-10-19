import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_senha
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioUpdate


async def criar_usuario(db: AsyncSession, dados: UsuarioCreate) -> Usuario:
    """Cria um novo usuário. E-mail/senha podem ser nulos para dizimistas."""
    if dados.email:
        resultado = await db.execute(
            select(Usuario).where(Usuario.email == dados.email)
        )
        if resultado.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe um usuário cadastrado com este e-mail.",
            )

    senha_para_hash = dados.senha or str(uuid.uuid4())

    usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        senha_hash=hash_senha(senha_para_hash),
        telefone=dados.telefone,
        data_nascimento=dados.data_nascimento,
        perfil=dados.perfil,
        paroquia_id=dados.paroquia_id,
    )

    db.add(usuario)
    await db.commit()
    await db.refresh(usuario)
    return usuario


async def buscar_usuario_por_id(db: AsyncSession, usuario_id) -> Usuario | None:
    resultado = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    return resultado.scalar_one_or_none()


async def atualizar_usuario(
    db: AsyncSession, usuario: Usuario, dados: UsuarioUpdate
) -> Usuario:
    """Atualiza os dados de um usuário existente."""
    if dados.email and dados.email != usuario.email:
        resultado = await db.execute(
            select(Usuario).where(Usuario.email == dados.email)
        )
        if resultado.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe um usuário cadastrado com este e-mail.",
            )

    usuario.nome = dados.nome
    # E-mail pode ser None para dizimistas cadastrados sem acesso ao sistema.
    usuario.email = dados.email
    usuario.telefone = dados.telefone
    usuario.data_nascimento = dados.data_nascimento
    usuario.perfil = dados.perfil
    usuario.paroquia_id = dados.paroquia_id
    usuario.ativo = dados.ativo

    await db.commit()
    await db.refresh(usuario)
    return usuario


async def excluir_usuario(db: AsyncSession, usuario: Usuario) -> None:
    """
    Exclusão lógica (soft delete) do usuário.
    """
    if usuario.excluido_em is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Usuário já foi excluído.",
        )

    usuario.nome = "Usuário excluído"
    usuario.email = f"excluido+{uuid.uuid4().hex[:10]}@anonimizado.local"
    usuario.telefone = None
    usuario.data_nascimento = None
    usuario.senha_hash = ""
    usuario.ativo = False
    usuario.excluido_em = datetime.now(UTC)

    if usuario.perfil_dizimista is not None:
        usuario.perfil_dizimista.endereco = None
        usuario.perfil_dizimista.bairro = None
        usuario.perfil_dizimista.cidade = None

    await db.commit()
