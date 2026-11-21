"""service request complaint flag

Additive only: `service_requests.is_complaint` marks the marketer's «إرسال شكوى
للمالك» (Table 5). The complaint is addressed to the owner alone (§11), but the
row also carries a company id, so company scope alone let a manager or developer
of the same company read it. The flag lets the list and the detail view keep it
to its recipient.

Revision ID: b7c1f4d92e35
Revises: d4e5f6a7b8c9
Create Date: 2026-11-17 18:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b7c1f4d92e35'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'service_requests',
        sa.Column('is_complaint', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )
    op.create_index('ix_service_requests_is_complaint', 'service_requests', ['is_complaint'])
    # Existing rows already in the table were created before the flag existed;
    # the complaint subject is the only durable marker they carry.
    op.execute(
        "UPDATE service_requests SET is_complaint = true "
        "WHERE subject IN ('شكوى للمالك', 'Complaint to the owner')"
    )


def downgrade() -> None:
    op.drop_index('ix_service_requests_is_complaint', table_name='service_requests')
    op.drop_column('service_requests', 'is_complaint')
