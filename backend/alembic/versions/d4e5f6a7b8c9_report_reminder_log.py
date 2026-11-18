"""report reminder log for idempotent deadline reminders

Additive only: one new table so the reminder job can record, per company, period,
calendar day and reminder kind, that a reminder was handled. The unique constraint
is what makes the job idempotent across repeated runs and concurrent workers.

Revision ID: d4e5f6a7b8c9
Revises: f1a2b3c4d5e6
Create Date: 2026-11-18 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'report_reminder_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=False),
        sa.Column('reminder_date', sa.Date(), nullable=False),
        sa.Column('kind', sa.String(length=24), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('recipient_email', sa.String(length=255), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['period_id'], ['reporting_periods.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', 'period_id', 'reminder_date', 'kind', name='uq_reminder_company_period_date_kind'),
    )
    op.create_index('ix_report_reminder_logs_company_id', 'report_reminder_logs', ['company_id'])
    op.create_index('ix_report_reminder_logs_period_id', 'report_reminder_logs', ['period_id'])
    op.create_index('ix_report_reminder_logs_reminder_date', 'report_reminder_logs', ['reminder_date'])
    op.create_index('ix_report_reminder_logs_status', 'report_reminder_logs', ['status'])


def downgrade() -> None:
    op.drop_index('ix_report_reminder_logs_status', table_name='report_reminder_logs')
    op.drop_index('ix_report_reminder_logs_reminder_date', table_name='report_reminder_logs')
    op.drop_index('ix_report_reminder_logs_period_id', table_name='report_reminder_logs')
    op.drop_index('ix_report_reminder_logs_company_id', table_name='report_reminder_logs')
    op.drop_table('report_reminder_logs')
