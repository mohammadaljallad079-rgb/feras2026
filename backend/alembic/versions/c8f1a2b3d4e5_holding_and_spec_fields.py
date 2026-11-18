"""holding flag plus the remaining Table 5 fields

Additive only, so the running platform and its data are untouched:

* `companies.is_holding` — §7.1/§7.4: the Holding keeps its own monthly report
  alongside the subsidiaries.
* `accounting_entries.tax_registration_no` / `.service_item` — Table 5,
  «إيراد / فاتورة جديدة».
* `employees.contract_summary`, `.official_documents_file_id`,
  `.employment_contract_file_id` — Table 5, «إضافة موظف».

Revision ID: c8f1a2b3d4e5
Revises: b5e6f7a8c9d0
Create Date: 2026-11-17 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c8f1a2b3d4e5'
down_revision: Union[str, None] = 'b5e6f7a8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'companies',
        sa.Column('is_holding', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index('ix_companies_is_holding', 'companies', ['is_holding'])

    op.add_column('accounting_entries', sa.Column('tax_registration_no', sa.String(length=64), nullable=True))
    op.add_column('accounting_entries', sa.Column('service_item', sa.String(length=255), nullable=True))

    op.add_column('employees', sa.Column('contract_summary', sa.Text(), nullable=True))
    op.add_column('employees', sa.Column('official_documents_file_id', sa.Integer(), nullable=True))
    op.add_column('employees', sa.Column('employment_contract_file_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_employees_official_documents_file_id',
        'employees',
        'stored_files',
        ['official_documents_file_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_employees_employment_contract_file_id',
        'employees',
        'stored_files',
        ['employment_contract_file_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_employees_employment_contract_file_id', 'employees', type_='foreignkey')
    op.drop_constraint('fk_employees_official_documents_file_id', 'employees', type_='foreignkey')
    op.drop_column('employees', 'employment_contract_file_id')
    op.drop_column('employees', 'official_documents_file_id')
    op.drop_column('employees', 'contract_summary')

    op.drop_column('accounting_entries', 'service_item')
    op.drop_column('accounting_entries', 'tax_registration_no')

    op.drop_index('ix_companies_is_holding', table_name='companies')
    op.drop_column('companies', 'is_holding')
