"""
Testes de integração para a migração 7319c1734504
(bloqueio de UPDATE/DELETE em audit_log via trigger).
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError, InternalError


@pytest.fixture
async def registro_audit_log(db_session):
    """Insere um registro em audit_log para servir de alvo nos testes
    de UPDATE/DELETE, e garante limpeza ao final (via rollback da sessão)."""
    registro_id = str(uuid.uuid4())
    result = await db_session.execute(
        text("""
            INSERT INTO audit_log (
            tabela, operacao, registro_id, dados_novos, executado_em)
            VALUES ('teste_tabela', 'INSERT', :registro_id, '{}'::jsonb, now())
            RETURNING id
        """),
        {"registro_id": registro_id},
    )
    await db_session.commit()
    row = result.fetchone()
    return row.id


class TestImutabilidadeAuditLog:
    async def test_insert_em_audit_log_funciona_normalmente(self, db_session):
        """Confirma que o caminho feliz (INSERT) não é afetado pelo trigger."""
        registro_id = str(uuid.uuid4())
        result = await db_session.execute(
            text("""
                INSERT INTO audit_log (
                tabela, operacao, registro_id, dados_novos, executado_em)
                VALUES (
                'teste_tabela', 'INSERT', :registro_id,
                '{"campo": "valor"}'::jsonb, now())
                RETURNING id
            """),
            {"registro_id": registro_id},
        )
        await db_session.commit()
        row = result.fetchone()
        assert row.id is not None

    async def test_update_em_audit_log_e_bloqueado(
        self, db_session, registro_audit_log
    ):
        with pytest.raises((DBAPIError, InternalError, IntegrityError)) as exc_info:
            await db_session.execute(
                text("UPDATE audit_log SET operacao = 'FORJADO' WHERE id = :id"),
                {"id": registro_audit_log},
            )
            await db_session.commit()

        await db_session.rollback()
        mensagem = str(exc_info.value).lower()
        assert "imutável" in mensagem or "não permitida" in mensagem

    async def test_delete_em_audit_log_e_bloqueado(
        self, db_session, registro_audit_log
    ):
        with pytest.raises((DBAPIError, InternalError, IntegrityError)) as exc_info:
            await db_session.execute(
                text("DELETE FROM audit_log WHERE id = :id"),
                {"id": registro_audit_log},
            )
            await db_session.commit()

        await db_session.rollback()
        mensagem = str(exc_info.value).lower()
        assert "imutável" in mensagem or "não permitida" in mensagem

    async def test_delete_em_massa_tambem_e_bloqueado(
        self, db_session, registro_audit_log
    ):
        with pytest.raises((DBAPIError, InternalError, IntegrityError)) as exc_info:
            await db_session.execute(text("DELETE FROM audit_log"))
            await db_session.commit()

        await db_session.rollback()
        mensagem = str(exc_info.value).lower()
        assert "imutável" in mensagem or "não permitida" in mensagem


class TestEstruturaDoBloqueio:
    async def test_funcao_fn_bloquear_alteracao_existe(self, db_session):
        result = await db_session.execute(
            text("""
                SELECT proname FROM pg_proc
                WHERE proname = 'fn_bloquear_alteracao_audit_log'
            """)
        )
        assert result.fetchone() is not None

    async def test_trigger_esta_ativo_em_audit_log(self, db_session):
        result = await db_session.execute(
            text("""
                SELECT trigger_name, event_manipulation
                FROM information_schema.triggers
                WHERE event_object_table = 'audit_log'
                  AND trigger_name = 'trg_bloquear_alteracao_audit_log'
                ORDER BY event_manipulation
            """)
        )
        eventos = {row.event_manipulation for row in result.fetchall()}
        assert eventos == {"DELETE", "UPDATE"}
