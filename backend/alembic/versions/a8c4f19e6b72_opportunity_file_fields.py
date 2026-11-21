"""opportunity file: classification, financials, risk, follow-up, outcome

Additive only. Every column is nullable, so the opportunity workflow the brief
defines (§5.1 and Table 5) keeps working unchanged and an opportunity created
with just topic, country and file is still complete.

Revision ID: a8c4f19e6b72
Revises: d5b8e2f61a37
Create Date: 2026-11-17 16:05:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a8c4f19e6b72'
down_revision: Union[str, None] = 'd5b8e2f61a37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('opportunities', sa.Column('category', sa.String(length=24), nullable=True))
    op.add_column('opportunities', sa.Column('requested_from_group', sa.Text(), nullable=True))
    op.add_column('opportunities', sa.Column('investment_amount', sa.Numeric(18, 2), nullable=True))
    op.add_column('opportunities', sa.Column('expected_return', sa.Numeric(18, 2), nullable=True))
    op.add_column('opportunities', sa.Column('expected_return_pct', sa.Numeric(9, 2), nullable=True))
    op.add_column('opportunities', sa.Column('cashflow_note', sa.Text(), nullable=True))
    op.add_column('opportunities', sa.Column('risk_level', sa.String(length=16), nullable=True))
    op.add_column('opportunities', sa.Column('risk_note', sa.Text(), nullable=True))
    op.add_column('opportunities', sa.Column('recommendation', sa.Text(), nullable=True))
    op.add_column('opportunities', sa.Column('next_step_owner_id', sa.Integer(), nullable=True))
    op.add_column('opportunities', sa.Column('next_step_on', sa.Date(), nullable=True))
    op.add_column('opportunities', sa.Column('actual_return', sa.Numeric(18, 2), nullable=True))
    op.add_column('opportunities', sa.Column('actual_note', sa.Text(), nullable=True))
    op.create_foreign_key(
        'fk_opportunities_next_step_owner_id_users',
        'opportunities', 'users', ['next_step_owner_id'], ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_opportunities_next_step_owner_id_users', 'opportunities', type_='foreignkey')
    for column in (
        'actual_note', 'actual_return', 'next_step_on', 'next_step_owner_id',
        'recommendation', 'risk_note', 'risk_level', 'cashflow_note',
        'expected_return_pct', 'expected_return', 'investment_amount',
        'requested_from_group', 'category',
    ):
        op.drop_column('opportunities', column)
