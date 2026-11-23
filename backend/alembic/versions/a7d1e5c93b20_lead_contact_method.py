"""lead contact method

Additive only: `leads.contact_method` records how the lead prefers to be
reached (Table 6, «عميل محتمل جديد»: «وسيلة التواصل»), kept separate from the
contact value itself.

Revision ID: a7d1e5c93b20
Revises: c8f1a2b3d4e5
Create Date: 2026-11-17 16:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7d1e5c93b20'
down_revision: Union[str, None] = 'c8f1a2b3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('leads', sa.Column('contact_method', sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column('leads', 'contact_method')
