"""torna usuario email nullable para dizimista sem acesso

Revision ID: 18a6a943563d
Revises: 6fc58f64d9a2
Create Date: 2026-10-19 20:52:18.699053

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '18a6a943563d'
down_revision: Union[str, Sequence[str], None] = '6fc58f64d9a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("usuario", "email", nullable=True)


def downgrade() -> None:
    op.alter_column("usuario", "email", nullable=False)
    
    # ### end Alembic commands ###
