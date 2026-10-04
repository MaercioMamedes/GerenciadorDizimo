"""cria funcao de trigger fn_audit_log

Revision ID: 05a81bfaad2a
Revises: b98a8b91d440
Create Date: 2026-10-01 16:54:31.209726

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '05a81bfaad2a'
down_revision: Union[str, Sequence[str], None] = 'b98a8b91d440'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


"""cria função de trigger de auditoria fn_audit_log"""


FN_AUDIT_LOG_UP = """
CREATE OR REPLACE FUNCTION fn_audit_log() RETURNS TRIGGER AS $$
DECLARE
    v_usuario_id uuid;
    v_dados_anteriores jsonb;
    v_dados_novos jsonb;
    v_registro_id uuid;
BEGIN
    -- Tenta ler o usuario_id propagado via SET LOCAL na sessão (Fase 2)
    BEGIN
        v_usuario_id := current_setting('app.usuario_id', true)::uuid;
    EXCEPTION WHEN OTHERS THEN
        v_usuario_id := NULL;
    END;

    IF TG_OP = 'INSERT' THEN
        v_dados_anteriores := NULL;
        v_dados_novos := to_jsonb(NEW);
        v_registro_id := NEW.id;
    ELSIF TG_OP = 'UPDATE' THEN
        v_dados_anteriores := to_jsonb(OLD);
        v_dados_novos := to_jsonb(NEW);
        v_registro_id := NEW.id;
    ELSIF TG_OP = 'DELETE' THEN
        v_dados_anteriores := to_jsonb(OLD);
        v_dados_novos := NULL;
        v_registro_id := OLD.id;
    END IF;

    INSERT INTO audit_log (
        tabela, operacao, registro_id,
        dados_anteriores, dados_novos,
        usuario_id, executado_em
    )
    VALUES (
        TG_TABLE_NAME, TG_OP, v_registro_id,
        v_dados_anteriores, v_dados_novos,
        v_usuario_id, now()
    );

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;
"""

FN_AUDIT_LOG_DOWN = "DROP FUNCTION IF EXISTS fn_audit_log();"


def upgrade() -> None:
    op.execute(FN_AUDIT_LOG_UP)


def downgrade() -> None:
    op.execute(FN_AUDIT_LOG_DOWN)

