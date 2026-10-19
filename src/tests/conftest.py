"""Fixtures compartilhadas:
mock para testes de CRUD e engine real para testes de conexao."""


import asyncio
import contextlib
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from alembic import command
from app.core.config import settings
from app.core.security import hash_senha
from app.db.session import get_db
from app.main import app
from app.models.igreja import Igreja
from app.models.paroquia import Paroquia
from app.models.usuario import PerfilUsuario, Usuario

# from app.models.base import Base  # mantido: outras fixtures/testes podem usar Base

# ---------------------------------------------------------------------------
# Fixtures para testes de INTEGRACAO (banco real)
# ---------------------------------------------------------------------------

TEST_DB_NAME = f"{settings.postgres_db}_test"
TEST_DATABASE_URL = (
    f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
    f"@{settings.postgres_host}:{settings.postgres_port}/{TEST_DB_NAME}"
)
MAINTENANCE_DATABASE_URL = (
    f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
    f"@{settings.postgres_host}:{settings.postgres_port}/postgres"
)

# Raiz do projeto: src/tests/conftest.py -> sobe 2 niveis
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI_PATH = PROJECT_ROOT / "alembic.ini"



async def _ensure_test_database_exists() -> None:
    """Conecta ao banco de manutencao 'postgres'
    e cria o banco de teste, se nao existir."""
    maintenance_engine = create_async_engine(
        MAINTENANCE_DATABASE_URL,
        isolation_level="AUTOCOMMIT",
    )
    try:
        async with maintenance_engine.connect() as conn:
            with contextlib.suppress(ProgrammingError):
                await conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    finally:
        await maintenance_engine.dispose()


def _run_alembic_upgrade(sync_url: str) -> None:
    """
    Executa `alembic upgrade head` de forma sincrona (API do Alembic eh
    sincrona), apontando explicitamente para o banco de teste via
    config.attributes — sem alterar o comportamento padrao do env.py
    usado em producao/dev.
    """
    alembic_cfg = Config(str(ALEMBIC_INI_PATH))
    alembic_cfg.attributes["sqlalchemy_url"] = sync_url
    command.upgrade(alembic_cfg, "head")


@pytest_asyncio.fixture
async def admin_factory(db_session: AsyncSession):
    """
    Cria um administrador vinculado a uma paroquia e igreja matriz de teste.
    Retorna o objeto Usuario criado (com paroquia_id preenchido).
    """

    async def _factory(session: AsyncSession | None = None) -> Usuario:
        session = session or db_session

        # 1) Cria paroquia vazia (nome vem da igreja matriz)
        paroquia = Paroquia()
        session.add(paroquia)
        await session.flush()
        await session.refresh(paroquia)

        # 2) Cria igreja matriz vinculada (define o nome da paroquia)
        matriz = Igreja(
            nome=f"Paroquia {uuid.uuid4().hex[:8]}",
            is_matriz=True,
            paroquia_id=paroquia.id,
        )
        session.add(matriz)
        await session.flush()
        await session.refresh(paroquia)  # atualiza a property matriz/nome
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
    Cria uma igreja de teste vinculada a uma paroquia.
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


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def engine():
    """
    Garante que o banco de teste existe e aplica TODAS as migracoes
    Alembic reais nele (nao apenas Base.metadata.create_all), garantindo
    que funcoes, triggers e demais objetos criados via `op.execute()`
    tambem existam no banco de teste.
    """
    await _ensure_test_database_exists()

    # Alembic/psycopg2 operam de forma sincrona; a URL assincrona (+asyncpg)
    # nao serve aqui — removemos o driver para usar o padrao (psycopg2)
    sync_test_url = TEST_DATABASE_URL.replace("+asyncpg", "")

    # command.upgrade eh bloqueante; roda em thread separada para nao
    # travar o event loop do pytest-asyncio
    await asyncio.to_thread(_run_alembic_upgrade, sync_test_url)

    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    yield test_engine

    # Derruba todo o schema (mais simples e confiavel que rodar
    # downgrade migracao por migracao)
    async with test_engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))

    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Sessao real, isolada por teste, usando savepoints (nested transactions).

    Mesmo que o codigo sob teste chame `session.commit()`, o commit real
    fica "preso" dentro de uma transacao externa que nunca eh confirmada.
    Ao final do teste, fazemos rollback da transacao externa, desfazendo
    TUDO que foi persistido, independentemente de quantos commits ocorreram.
    """
    connection = await engine.connect()
    trans = await connection.begin()

    async_session = async_sessionmaker(
        bind=connection, expire_on_commit=False, class_=AsyncSession
    )
    session = async_session()

    nested = await connection.begin_nested()

    @event.listens_for(session.sync_session, "after_transaction_end")
    def restart_savepoint(sync_session, transaction):
        nonlocal nested
        if not nested.is_active:
            nested = connection.sync_connection.begin_nested()

    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await connection.close()


# ---------------------------------------------------------------------------
# Fixture async_client: cliente HTTP assincrono para testes de views
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator:
    """
    Cliente HTTP assincrono (httpx.AsyncClient) para testar endpoints FastAPI.

    Sobrescreve a dependencia `get_db` para usar a `db_session` do teste,
    garantindo que as operacoes rodem dentro do savepoint e sejam revertidas
    ao final do teste.
    """


    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()



# ---------------------------------------------------------------------------
# Fixture para testes de UNIDADE (mock, sem infraestrutura)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_session():
    """
    Simula uma AsyncSession do SQLAlchemy.

    Uso tipico:
        mock_session.add(obj)
        await mock_session.commit()
        mock_session.add.assert_called_once_with(obj)
    """
    session = MagicMock(spec=AsyncSession)
    session.add = MagicMock()
    session.delete = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    session.get = AsyncMock()
    return session
