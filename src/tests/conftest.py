"""Fixtures compartilhadas: mock para testes de CRUD e engine real para testes de conexão."""
import contextlib
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.base import Base

# ---------------------------------------------------------------------------
# Fixtures para testes de INTEGRAÇÃO (banco real)
# ---------------------------------------------------------------------------

TEST_DB_NAME = f"{settings.postgres_db}_test"

# URL apontando para o banco de teste (usado pela engine principal)
TEST_DATABASE_URL = settings.database_url.replace(settings.postgres_db, TEST_DB_NAME)

# URL apontando para o banco "postgres" padrão, usado só para criar o banco de teste
MAINTENANCE_DATABASE_URL = settings.database_url.replace(settings.postgres_db, "postgres")


async def _ensure_test_database_exists() -> None:
    """Conecta ao banco de manutenção 'postgres' e cria o banco de teste, se não existir."""
    maintenance_engine = create_async_engine(
        MAINTENANCE_DATABASE_URL,
        isolation_level="AUTOCOMMIT",  # CREATE DATABASE não pode rodar em transação
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
    """Sessão real, isolada por teste, com rollback automático."""
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session() as session:
        yield session
        await session.rollback()


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
