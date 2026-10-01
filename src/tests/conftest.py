"""Fixtures compartilhadas: 
mock para testes de CRUD e engine real para testes de conexão."""

import contextlib
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import event, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.base import Base

# ---------------------------------------------------------------------------
# Fixtures para testes de INTEGRAÇÃO (banco real)
# ---------------------------------------------------------------------------

TEST_DB_NAME = f"{settings.postgres_db}_test"

TEST_DATABASE_URL = settings.database_url.replace(settings.postgres_db, TEST_DB_NAME)
MAINTENANCE_DATABASE_URL = settings.database_url.replace(
    settings.postgres_db, "postgres"
)


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


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def engine():
    """
    Garante que o banco de teste existe, cria o engine assíncrono real
    e as tabelas antes da suíte de integração.
    """
    await _ensure_test_database_exists()

    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield test_engine

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

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

    # Inicia o primeiro savepoint
    nested = await connection.begin_nested()

    @event.listens_for(session.sync_session, "after_transaction_end")
    def restart_savepoint(sync_session, transaction):
        """
        Sempre que o savepoint atual é finalizado (por causa de um commit()
        do código sob teste), abre um novo savepoint imediatamente,
        para que o próximo commit também fique contido.
        """
        nonlocal nested
        if not nested.is_active:
            nested = connection.sync_connection.begin_nested()

    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()  # desfaz TUDO, mesmo commits explícitos
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
