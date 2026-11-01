"""Fixtures específicas para testes de unidade."""

import uuid
from datetime import date

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_senha
from app.models.igreja import Igreja
from app.models.paroquia import Paroquia
from app.models.perfil_dizimista import PerfilDizimista, StatusCadastro
from app.models.usuario import PerfilUsuario, Usuario


@pytest_asyncio.fixture
async def admin_factory(db_session: AsyncSession):
    """
    Cria um administrador vinculado a uma paróquia e igreja matriz de teste.
    """

    async def _factory(session: AsyncSession | None = None) -> Usuario:
        session = session or db_session

        paroquia = Paroquia()
        session.add(paroquia)
        await session.flush()
        await session.refresh(paroquia)

        matriz = Igreja(
            nome=f"Paroquia {uuid.uuid4().hex[:8]}",
            is_matriz=True,
            paroquia_id=paroquia.id,
        )
        session.add(matriz)
        await session.flush()
        await session.refresh(paroquia)
        await session.refresh(matriz)

        admin = Usuario(
            nome="Administrador Teste",
            email=f"admin-{uuid.uuid4().hex[:8]}@teste.local",
            senha_hash=hash_senha("Senha@123"),
            perfil=PerfilUsuario.ADMINISTRADOR,
            ativo=True,
            paroquia_id=paroquia.id,
        )

        session.add(admin)
        await session.flush()
        await session.refresh(admin)
        return admin

    return _factory


@pytest_asyncio.fixture
async def igreja_factory(db_session: AsyncSession):
    """
    Cria uma igreja de teste vinculada a uma paróquia.
    """

    async def _factory(
        session: AsyncSession | None = None,
        paroquia_id: uuid.UUID | None = None,
        nome: str = "Igreja Teste",
    ) -> Igreja:
        session = session or db_session

        if paroquia_id is None:
            paroquia = Paroquia()
            session.add(paroquia)
            await session.flush()
            await session.refresh(paroquia)

            matriz = Igreja(
                nome=f"Paroquia {uuid.uuid4().hex[:8]}",
                is_matriz=True,
                paroquia_id=paroquia.id,
            )
            session.add(matriz)
            await session.flush()
            await session.refresh(paroquia)
            paroquia_id = paroquia.id

        igreja = Igreja(nome=nome, paroquia_id=paroquia_id)
        session.add(igreja)
        await session.flush()
        await session.refresh(igreja)
        return igreja

    return _factory

@pytest_asyncio.fixture
async def paroquia_padrao(db_session: AsyncSession) -> Paroquia:
    """Cria uma paróquia base para os usuários dos testes."""
    paroquia = Paroquia()
    db_session.add(paroquia)
    await db_session.flush()
    await db_session.refresh(paroquia)

    matriz = Igreja(
        nome="Paróquia Teste Filtros",
        paroquia_id=paroquia.id,
        is_matriz=True,
    )
    db_session.add(matriz)
    await db_session.flush()
    await db_session.refresh(paroquia)

    return paroquia



@pytest_asyncio.fixture
async def igreja_padrao(db_session: AsyncSession, paroquia_padrao: Paroquia) -> Igreja:
    igreja = Igreja(
        nome="Igreja Matriz Filtros",
        paroquia_id=paroquia_padrao.id,
        is_matriz=True,
    )
    db_session.add(igreja)
    await db_session.flush()
    await db_session.refresh(igreja)
    return igreja


@pytest_asyncio.fixture
async def usuarios_filtro(
    db_session: AsyncSession,
    paroquia_padrao: Paroquia,
    igreja_padrao: Igreja,
) -> dict[str, Usuario]:
    admin_ativo = Usuario(
        nome="João Admin",
        email="joao.admin@example.com",
        senha_hash=hash_senha("senha123"),
        perfil=PerfilUsuario.ADMINISTRADOR,
        ativo=True,
        paroquia_id=paroquia_padrao.id,
    )

    admin_inativo = Usuario(
        nome="Maria Admin Inativa",
        email="maria.admin@example.com",
        senha_hash=hash_senha("senha123"),
        perfil=PerfilUsuario.ADMINISTRADOR,
        ativo=False,
        paroquia_id=paroquia_padrao.id,
    )

    dizimista_aprovado = Usuario(
        nome="Carlos Dizimista",
        email="carlos@example.com",
        senha_hash=hash_senha("senha123"),
        perfil=PerfilUsuario.DIZIMISTA,
        ativo=True,
        data_nascimento=date(1985, 6, 15),
        paroquia_id=paroquia_padrao.id,
    )
    perfil_carlos = PerfilDizimista(
        usuario=dizimista_aprovado,
        numero_registro=1234,
        status_cadastro=StatusCadastro.APROVADO,
        igreja_id=igreja_padrao.id,
    )

    dizimista_pendente = Usuario(
        nome="Ana Dizimista",
        email="ana@example.com",
        senha_hash=hash_senha("senha123"),
        perfil=PerfilUsuario.DIZIMISTA,
        ativo=False,
        data_nascimento=date(1990, 3, 22),
        paroquia_id=paroquia_padrao.id,
    )
    perfil_ana = PerfilDizimista(
        usuario=dizimista_pendente,
        numero_registro=5678,
        status_cadastro=StatusCadastro.PENDENTE,
        igreja_id=igreja_padrao.id,
    )

    dizimista_rejeitado = Usuario(
        nome="Bruno Rejeitado",
        email="bruno@example.com",
        perfil=PerfilUsuario.DIZIMISTA,
        ativo=True,
        paroquia_id=paroquia_padrao.id,
        senha_hash=hash_senha("senha123"),
    )
    perfil_bruno = PerfilDizimista(
        usuario=dizimista_rejeitado,
        numero_registro=None,
        status_cadastro=StatusCadastro.REJEITADO,
        igreja_id=igreja_padrao.id,
    )

    db_session.add_all(
        [
            admin_ativo,
            admin_inativo,
            dizimista_aprovado,
            dizimista_pendente,
            dizimista_rejeitado,
            perfil_carlos,
            perfil_ana,
            perfil_bruno,
        ]
    )
    await db_session.commit()

    return {
        "admin_ativo": admin_ativo,
        "admin_inativo": admin_inativo,
        "dizimista_aprovado": dizimista_aprovado,
        "dizimista_pendente": dizimista_pendente,
        "dizimista_rejeitado": dizimista_rejeitado,
    }
