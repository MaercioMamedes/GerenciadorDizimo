# src/tests/test_fn_audit_log_trigger.py
"""
Testes de integração para a função de trigger fn_audit_log (Fase 3).

A função só tem efeito quando associada a um trigger em uma tabela.
Criamos uma tabela temporária de teste, anexamos o trigger fn_audit_log
a ela, e validamos o comportamento de INSERT/UPDATE/DELETE em audit_log.

Como db_session roda dentro de savepoints revertidos ao final do teste
(ver conftest.py), não é necessário DROP TABLE explícito: toda a DDL e
DML executada aqui é desfeita automaticamente no rollback da fixture.
"""

import uuid

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def tabela_teste_com_trigger(db_session):
    """Cria tabela temporária e anexa o trigger fn_audit_log a ela."""
    await db_session.execute(
        text("""
        CREATE TABLE tabela_teste_audit (
            id uuid PRIMARY KEY,
            nome text
        );
    """)
    )
    await db_session.execute(
        text("""
        CREATE TRIGGER trg_audit_tabela_teste
        AFTER INSERT OR UPDATE OR DELETE ON tabela_teste_audit
        FOR EACH ROW EXECUTE FUNCTION fn_audit_log();
    """)
    )
    await db_session.commit()
    return "tabela_teste_audit"


async def test_fn_audit_log_registra_insert(db_session, tabela_teste_com_trigger):
    usuario_id = uuid.uuid4()
    registro_id = uuid.uuid4()

    await db_session.execute(
        text("SELECT set_config('app.usuario_id', :uid, true)"),
        {"uid": str(usuario_id)},
    )
    await db_session.execute(
        text("INSERT INTO tabela_teste_audit (id, nome) VALUES (:id, :nome)"),
        {"id": str(registro_id), "nome": "registro inicial"},
    )
    await db_session.commit()

    result = await db_session.execute(
        text("""
        SELECT tabela, operacao, dados_anteriores, dados_novos, usuario_id
        FROM audit_log
        WHERE tabela = 'tabela_teste_audit'
        ORDER BY executado_em DESC
        LIMIT 1
    """)
    )
    log = result.fetchone()

    assert log is not None
    assert log.tabela == "tabela_teste_audit"
    assert log.operacao == "INSERT"
    assert log.dados_anteriores is None
    assert log.dados_novos["nome"] == "registro inicial"
    assert str(log.usuario_id) == str(usuario_id)


async def test_fn_audit_log_registra_update_com_diff(
    db_session, tabela_teste_com_trigger
):
    usuario_id = uuid.uuid4()
    registro_id = uuid.uuid4()

    await db_session.execute(
        text("SELECT set_config('app.usuario_id', :uid, true)"),
        {"uid": str(usuario_id)},
    )
    await db_session.execute(
        text("INSERT INTO tabela_teste_audit (id, nome) VALUES (:id, 'antes')"),
        {"id": str(registro_id)},
    )
    await db_session.commit()

    await db_session.execute(
        text("SELECT set_config('app.usuario_id', :uid, true)"),
        {"uid": str(usuario_id)},
    )
    await db_session.execute(
        text("UPDATE tabela_teste_audit SET nome = 'depois' WHERE id = :id"),
        {"id": str(registro_id)},
    )
    await db_session.commit()

    result = await db_session.execute(
        text("""
        SELECT operacao, dados_anteriores, dados_novos
        FROM audit_log
        WHERE tabela = 'tabela_teste_audit' AND operacao = 'UPDATE'
        ORDER BY executado_em DESC
        LIMIT 1
    """)
    )
    log = result.fetchone()

    assert log is not None
    assert log.dados_anteriores["nome"] == "antes"
    assert log.dados_novos["nome"] == "depois"


async def test_fn_audit_log_registra_delete(db_session, tabela_teste_com_trigger):
    usuario_id = uuid.uuid4()
    registro_id = uuid.uuid4()

    await db_session.execute(
        text("SELECT set_config('app.usuario_id', :uid, true)"),
        {"uid": str(usuario_id)},
    )
    await db_session.execute(
        text("INSERT INTO tabela_teste_audit (id, nome) VALUES (:id, 'a excluir')"),
        {"id": str(registro_id)},
    )
    await db_session.commit()

    await db_session.execute(
        text("SELECT set_config('app.usuario_id', :uid, true)"),
        {"uid": str(usuario_id)},
    )
    await db_session.execute(
        text("DELETE FROM tabela_teste_audit WHERE id = :id"),
        {"id": str(registro_id)},
    )
    await db_session.commit()

    result = await db_session.execute(
        text("""
        SELECT operacao, dados_anteriores, dados_novos
        FROM audit_log
        WHERE tabela = 'tabela_teste_audit' AND operacao = 'DELETE'
        ORDER BY executado_em DESC
        LIMIT 1
    """)
    )
    log = result.fetchone()

    assert log is not None
    assert log.dados_anteriores["nome"] == "a excluir"
    assert log.dados_novos is None


async def test_fn_audit_log_sem_usuario_id_grava_null(
    db_session, tabela_teste_com_trigger
):
    """Se app.usuario_id não foi setado na sessão, a operação não deve quebrar."""
    registro_id = uuid.uuid4()

    await db_session.execute(
        text("INSERT INTO tabela_teste_audit (id, nome) VALUES (:id, 'sem usuario')"),
        {"id": str(registro_id)},
    )
    await db_session.commit()

    result = await db_session.execute(
        text("""
        SELECT usuario_id FROM audit_log
        WHERE tabela = 'tabela_teste_audit'
        ORDER BY executado_em DESC
        LIMIT 1
    """)
    )
    log = result.fetchone()

    assert log is not None
    assert log.usuario_id is None
