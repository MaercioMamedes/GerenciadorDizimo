"""adiciona numero_registro em perfil_dizimista

Revision ID: 6fc58f64d9a2
Revises: c8a03555b813
Create Date: 2026-10-17 12:30:30.012571

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6fc58f64d9a2"
down_revision: Union[str, Sequence[str], None] = "c8a03555b813"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Adiciona coluna numero_registro como opcional (nullable).
    op.add_column(
        "perfil_dizimista",
        sa.Column("numero_registro", sa.Integer(), nullable=True),
    )

    # Cria constraint nomeada para permitir rollback e facilitar manutenção.
    op.create_unique_constraint(
        "uq_perfil_dizimista_numero_registro",
        "perfil_dizimista",
        ["numero_registro"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "uq_perfil_dizimista_numero_registro",
        "perfil_dizimista",
        type_="unique",
    )
    op.drop_column("perfil_dizimista", "numero_registro")
