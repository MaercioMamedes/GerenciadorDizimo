"""Fixtures compartilhadas:
mock para testes de CRUD e engine real para testes de conexão."""

import asyncio
import contextlib
from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from alembic.config import Config
from sqlalchemy import event, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from alembic import command
from app.core.config import settings

# from app.models.base import Base  # mantido: outras fixtures/testes podem usar Base

# ---------------------------------------------------------------------------
# Fixtures para testes de INTEGRAÇÃO (banco real)
# ---------------------------------------------------------------------------

TEST_DB_NAME = f"{settings.postgres_db}_test"

TEST_DATABASE_URL = settings.database_url.replace(settings.postgres_db, TEST_DB_NAME)
MAINTENANCE_DATABASE_URL = settings.database_url.replace(
    settings.postgres_db, "postgres"
)

# Raiz do projeto: src/tests/conftest.py -> sobe 2 níveis
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI_PATH = PROJECT_ROOT / "alembic.ini"


async def _ensure_test_database_exists() -> None:
    """Conecta ao banco de manutenção 'postgres'
    e cria o banco de teste, se não existir."""
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
    Executa `alembic upgrade head` de forma síncrona (API do Alembic é
    síncrona), apontando explicitamente para o banco de teste via
    config.attributes — sem alterar o comportamento padrão do env.py
    usado em produção/dev.
    """
    alembic_cfg = Config(str(ALEMBIC_INI_PATH))
    alembic_cfg.attributes["sqlalchemy_url"] = sync_url
    command.upgrade(alembic_cfg, "head")


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def engine():
    """
    Garante que o banco de teste existe e aplica TODAS as migrações
    Alembic reais nele (não apenas Base.metadata.create_all), garantindo
    que funções, triggers e demais objetos criados via `op.execute()`
    também existam no banco de teste.
    """
    await _ensure_test_database_exists()

    # Alembic/psycopg2 operam de forma síncrona; a URL assíncrona (+asyncpg)
    # não serve aqui — removemos o driver para usar o padrão (psycopg2)
    sync_test_url = TEST_DATABASE_URL.replace("+asyncpg", "")

    # command.upgrade é bloqueante; roda em thread separada para não
    # travar o event loop do pytest-asyncio
    await asyncio.to_thread(_run_alembic_upgrade, sync_test_url)

    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    yield test_engine

    # Derruba todo o schema (mais simples e confiável que rodar
    # downgrade migração por migração)
    async with test_engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))

    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Sessão real, isolada por teste, usando savepoints (nested transactions).

    Mesmo que o código sob teste chame `session.commit()`, o commit real
    fica "preso" dentro de uma transação externa que nunca é confirmada.
    Ao final do teste, fazemos rollback da transação externa, desfazendo
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
# Fixture para testes de UNIDADE (mock, sem infraestrutura)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_session():
    """
    Simula uma AsyncSession do SQLAlchemy.

    Uso típico:
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
