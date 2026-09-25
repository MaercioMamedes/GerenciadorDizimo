"""Testes de conectividade real com o banco de dados (SEM mock)."""
import pytest
from sqlalchemy import text, inspect

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_connection_is_alive(db_session):
    """Garante que a sessão real consegue executar uma query simples."""
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_all_tables_exist(engine):
    """Verifica se todas as tabelas do schema foram criadas corretamente no banco real."""
    expected_tables = {
        "paroquia", "igreja", "usuario", "perfil_dizimista",
        "contribuicao", "audit_log", "security_log",
        "consentimento_lgpd", "notificacao",
    }

    async with engine.connect() as conn:
        table_names = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names()
        )

    assert expected_tables.issubset(set(table_names))


@pytest.mark.asyncio
async def test_perfil_dizimista_tem_colunas_de_endereco(engine):
    """Confirma que as colunas endereco/bairro/cidade existem na tabela real."""
    async with engine.connect() as conn:
        columns = await conn.run_sync(
            lambda sync_conn: {
                col["name"] for col in inspect(sync_conn).get_columns("perfil_dizimista")
            }
        )

    assert {"endereco", "bairro", "cidade"}.issubset(columns)


@pytest.mark.asyncio
async def test_usuario_tem_colunas_telefone_e_nascimento(engine):
    """Confirma que as colunas telefone/data_nascimento existem na tabela real."""
    async with engine.connect() as conn:
        columns = await conn.run_sync(
            lambda sync_conn: {
                col["name"] for col in inspect(sync_conn).get_columns("usuario")
            }
        )

    assert {"telefone", "data_nascimento"}.issubset(columns)
