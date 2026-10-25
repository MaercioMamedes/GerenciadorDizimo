import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_senha
from app.models.perfil_dizimista import PerfilDizimista, StatusCadastro
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioUpdate


@dataclass
class PerfilDizimistaPayload:
    """Dados do perfil dizimista para orquestração dentro do service."""

    igreja_id: uuid.UUID
    numero_registro: int | None = None
    endereco: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    status_cadastro: StatusCadastro | None = None


async def criar_usuario(
    db: AsyncSession,
    dados: UsuarioCreate,
    perfil_dizimista: PerfilDizimistaPayload | None = None,
    ativo: bool = False,
) -> Usuario:
    """Cria um novo usuário, opcionalmente com perfil dizimista vinculado.

    Toda a operação ocorre em uma única transação.
    """
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
    await db.flush()
    await db.refresh(usuario)

    if perfil_dizimista:
        status_cadastro = perfil_dizimista.status_cadastro or StatusCadastro.PENDENTE

        novo_perfil = PerfilDizimista(
            usuario_id=usuario.id,
            igreja_id=perfil_dizimista.igreja_id,
            numero_registro=perfil_dizimista.numero_registro,
            endereco=perfil_dizimista.endereco,
            bairro=perfil_dizimista.bairro,
            cidade=perfil_dizimista.cidade,
            status_cadastro=status_cadastro,
        )
        db.add(novo_perfil)

    # O modelo nasce inativo; a ativação depende do contexto (admin ou autocadastro).
    usuario.ativo = ativo

    await db.commit()
    await db.refresh(usuario)
    return usuario


async def buscar_usuario_por_id(db: AsyncSession, usuario_id) -> Usuario | None:
    resultado = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    return resultado.scalar_one_or_none()


async def atualizar_usuario(
    db: AsyncSession,
    usuario: Usuario,
    dados: UsuarioUpdate,
    perfil_dizimista: PerfilDizimistaPayload | None = None,
) -> Usuario:
    """Atualiza os dados do usuário e orquestra o perfil dizimista.

    Cria, atualiza ou remove o perfil dizimista conforme os dados recebidos.
    """
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
    usuario.email = dados.email
    usuario.telefone = dados.telefone
    usuario.data_nascimento = dados.data_nascimento
    usuario.perfil = dados.perfil
    usuario.paroquia_id = dados.paroquia_id
    usuario.ativo = dados.ativo

    perfil_alterado = await _orquestrar_perfil_dizimista(
        db, usuario, perfil_dizimista
    )

    if perfil_alterado:
        usuario.atualizado_em = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(usuario)
    return usuario


async def _orquestrar_perfil_dizimista(
    db: AsyncSession,
    usuario: Usuario,
    perfil_dizimista: PerfilDizimistaPayload | None,
) -> bool:
    """Cria, atualiza ou remove o perfil dizimista conforme necessário.

    Retorna True se o perfil foi alterado, indicando que o
    ``usuario.atualizado_em`` deve ser atualizado.
    """
    if perfil_dizimista is None:
        return False

    perfil_alterado = False
    status_cadastro = perfil_dizimista.status_cadastro or StatusCadastro.PENDENTE

    if usuario.perfil_dizimista is None:
        novo_perfil = PerfilDizimista(
            usuario_id=usuario.id,
            igreja_id=perfil_dizimista.igreja_id,
            numero_registro=perfil_dizimista.numero_registro,
            endereco=perfil_dizimista.endereco,
            bairro=perfil_dizimista.bairro,
            cidade=perfil_dizimista.cidade,
            status_cadastro=status_cadastro,
        )
        db.add(novo_perfil)
        perfil_alterado = True
    else:
        usuario.perfil_dizimista.igreja_id = perfil_dizimista.igreja_id
        usuario.perfil_dizimista.numero_registro = perfil_dizimista.numero_registro
        usuario.perfil_dizimista.endereco = perfil_dizimista.endereco
        usuario.perfil_dizimista.bairro = perfil_dizimista.bairro
        usuario.perfil_dizimista.cidade = perfil_dizimista.cidade
        usuario.perfil_dizimista.status_cadastro = status_cadastro
        perfil_alterado = True

    return perfil_alterado


async def remover_perfil_dizimista(db: AsyncSession, usuario: Usuario) -> bool:
    """Remove o perfil dizimista do usuário, se existir.

    Retorna True se houve remoção.
    """
    if usuario.perfil_dizimista is None:
        return False

    await db.delete(usuario.perfil_dizimista)
    usuario.atualizado_em = datetime.now(timezone.utc)
    return True


async def excluir_usuario(db: AsyncSession, usuario: Usuario) -> None:
    """Exclusão lógica (soft delete) do usuário e anonimização do perfil."""
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
        usuario.perfil_dizimista.numero_registro = None
        usuario.perfil_dizimista.endereco = None
        usuario.perfil_dizimista.bairro = None
        usuario.perfil_dizimista.cidade = None

    await db.commit()
