"""add commercial register number to companies

The four-step company wizard collects the optional commercial register number
(design reference page 7: «رقم السجل التجاري (اختياري)»).

Revision ID: b1f4c2d7a9e0
Revises: 1974782639ac
Create Date: 2026-11-16 10:20:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b1f4c2d7a9e0'
down_revision: Union[str, None] = '1974782639ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('companies', sa.Column('commercial_register_no', sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column('companies', 'commercial_register_no')
