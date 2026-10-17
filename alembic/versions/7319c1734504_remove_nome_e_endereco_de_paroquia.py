"""remove nome e endereco de paroquia (redundantes com igreja matriz)

Revision ID: a1b2c3d4e5f6
Revises: 7319c1734504
Create Date: 2026-10-11 13:41:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "7319c1734504"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("paroquia", "nome")
    op.drop_column("paroquia", "endereco")


def downgrade() -> None:
    op.add_column(
        "paroquia",
        sa.Column("nome", sa.String(length=150),
                   nullable=False, server_default="Paróquia sem nome"),
    )
    op.add_column(
        "paroquia",
        sa.Column("endereco", sa.String(length=255), nullable=True),
    )
