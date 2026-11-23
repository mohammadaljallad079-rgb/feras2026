"""brief spec fields: company public profile and accounting settlement state

Additive only. New nullable columns so the running platform and its data are
untouched:

* `companies.public_activity_ar/en` and `companies.website_url` — the public
  activity text and optional live link edited from Website management (the
  owner's brief, Table 7).
* `accounting_entries.payment_status` — the settlement state of an expense
  (مسدد / غير مسدد) or a commission (مستحقة / مدفوعة / مستلمة) (Table 5).

Revision ID: f3c2d9a81b47
Revises: e9b3a1c7f204
Create Date: 2026-11-17 08:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f3c2d9a81b47'
down_revision: Union[str, None] = 'e9b3a1c7f204'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('companies', sa.Column('public_activity_ar', sa.Text(), nullable=True))
    op.add_column('companies', sa.Column('public_activity_en', sa.Text(), nullable=True))
    op.add_column('companies', sa.Column('website_url', sa.String(length=255), nullable=True))
    op.add_column('accounting_entries', sa.Column('payment_status', sa.String(length=16), nullable=True))
    op.add_column('service_requests', sa.Column('service_type', sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column('service_requests', 'service_type')
    op.drop_column('accounting_entries', 'payment_status')
    op.drop_column('companies', 'website_url')
    op.drop_column('companies', 'public_activity_en')
    op.drop_column('companies', 'public_activity_ar')
