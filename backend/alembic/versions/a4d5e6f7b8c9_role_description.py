"""brief spec fields: role description

Additive only. A new nullable column so the running platform and its data are
untouched:

* `roles.description` — the description the custom-role dialog records (Table 5).

Revision ID: a4d5e6f7b8c9
Revises: f3c2d9a81b47
Create Date: 2026-11-17 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a4d5e6f7b8c9'
down_revision: Union[str, None] = 'f3c2d9a81b47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('roles', sa.Column('description', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('roles', 'description')

