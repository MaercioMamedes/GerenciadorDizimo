"""Fixtures compartilhadas entre testes de unidade e integração."""

import asyncio
import contextlib
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
from app.db.session import get_db
from app.main import app

TEST_DB_NAME = f"{settings.postgres_db}_test"
TEST_DATABASE_URL = (
    f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
    f"@{settings.postgres_host}:{settings.postgres_port}/{TEST_DB_NAME}"
)
MAINTENANCE_DATABASE_URL = (
    f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
    f"@{settings.postgres_host}:{settings.postgres_port}/postgres"
)

# src/tests/conftest.py -> sobe 1 nível chega à raiz do projeto
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI_PATH = PROJECT_ROOT / "alembic.ini"


async def _ensure_test_database_exists() -> None:
    """Conecta ao banco de manutenção 'postgres' e cria o banco de teste, se não existir."""
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
    Executa `alembic upgrade head` de forma síncrona, apontando explicitamente
    para o banco de teste via config.attributes.
    """
    alembic_cfg = Config(str(ALEMBIC_INI_PATH))
    alembic_cfg.attributes["sqlalchemy_url"] = sync_url
    command.upgrade(alembic_cfg, "head")


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def engine():
    """
    Garante que o banco de teste existe e aplica todas as migrações Alembic.
    """
    await _ensure_test_database_exists()

    sync_test_url = TEST_DATABASE_URL.replace("+asyncpg", "")
    await asyncio.to_thread(_run_alembic_upgrade, sync_test_url)

    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    yield test_engine

    async with test_engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))

    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Sessão real isolada por teste, usando savepoints (nested transactions).
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


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator:
    """
    Cliente HTTP assíncrono (httpx.AsyncClient) para testar endpoints FastAPI.
    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def mock_session():
    """
    Simula uma AsyncSession do SQLAlchemy para testes de unidade.
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

def _run_alembic_upgrade(sync_url: str) -> None:
    if not ALEMBIC_INI_PATH.exists():
        raise FileNotFoundError(
            f"alembic.ini não encontrado em {ALEMBIC_INI_PATH}"
        )

    alembic_cfg = Config(str(ALEMBIC_INI_PATH))
    alembic_cfg.attributes["sqlalchemy_url"] = sync_url
    command.upgrade(alembic_cfg, "head")
