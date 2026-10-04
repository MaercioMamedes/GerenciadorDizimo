"""revogar update e delete em audit_log para dizimo_user

Revision ID: 7319c1734504
Revises: 05a81bfaad2a
Create Date: 2026-10-01 18:18:58.908428

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7319c1734504'
down_revision: Union[str, Sequence[str], None] = '05a81bfaad2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "dizimo_user"


def upgrade() -> None:
    """Upgrade schema."""
    # Camada extra de defesa (defense in depth): revoga UPDATE/DELETE da role
    # de aplicação em audit_log. Observação: como dizimo_user é owner/superuser
    # do banco atualmente, este REVOKE não tem efeito prático agora (owners e
    # superusers ignoram GRANT/REVOKE), mas documenta a intenção e passa a
    # valer caso a role deixe de ter esses privilégios no futuro.
    op.execute(f"REVOKE UPDATE, DELETE ON audit_log FROM {APP_ROLE};")

    # Bloqueio efetivo e à prova de falhas: trigger que impede UPDATE/DELETE
    # em audit_log independente de quem está conectado (inclusive owner/superuser).
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_bloquear_alteracao_audit_log()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION
                'Operação não permitida: audit_log é imutável (append-only).
                Tentativa de % bloqueada.',
                TG_OP;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trg_bloquear_alteracao_audit_log
        BEFORE UPDATE OR DELETE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION fn_bloquear_alteracao_audit_log();
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER IF EXISTS trg_bloquear_alteracao_audit_log ON audit_log;")
    op.execute("DROP FUNCTION IF EXISTS fn_bloquear_alteracao_audit_log();")
    op.execute(f"GRANT UPDATE, DELETE ON audit_log TO {APP_ROLE};")
