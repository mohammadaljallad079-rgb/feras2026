"""add party, tax and direction to accounting entries

Design reference page 9 splits holding accounting into three sections with their
own columns: expenses (البيان/المبلغ/الجهة/السداد), invoices
(العميل/الإجمالي قبل الضريبة/الضريبة/الإجمالي) and commissions
(الطرف/السبب/المبلغ/الاتجاه/الحالة).

Revision ID: c7a9e1b53d24
Revises: b1f4c2d7a9e0
Create Date: 2026-11-16 10:40:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c7a9e1b53d24'
down_revision: Union[str, None] = 'b1f4c2d7a9e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('accounting_entries', sa.Column('party', sa.String(length=255), nullable=True))
    op.add_column('accounting_entries', sa.Column('tax_amount', sa.Numeric(precision=18, scale=2), nullable=True))
    op.add_column('accounting_entries', sa.Column('direction', sa.String(length=16), nullable=True))


def downgrade() -> None:
    op.drop_column('accounting_entries', 'direction')
    op.drop_column('accounting_entries', 'tax_amount')
    op.drop_column('accounting_entries', 'party')
