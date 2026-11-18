"""assistant task flag

Additive only: `executive_directives.is_assistant_task` marks a directive the
AI assistant created through «نعم، أحلها لمطوّر الأعمال» (Table 6), so the
business developer's «مهام من المساعد» card counts those tasks rather than
every assistant query.

Revision ID: f1a2b3c4d5e6
Revises: a7d1e5c93b20
Create Date: 2026-11-17 16:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'a7d1e5c93b20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'executive_directives',
        sa.Column('is_assistant_task', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        'ix_executive_directives_is_assistant_task',
        'executive_directives',
        ['is_assistant_task'],
    )


def downgrade() -> None:
    op.drop_index('ix_executive_directives_is_assistant_task', table_name='executive_directives')
    op.drop_column('executive_directives', 'is_assistant_task')
