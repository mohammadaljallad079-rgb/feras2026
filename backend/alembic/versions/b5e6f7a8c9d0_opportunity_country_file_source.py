"""brief spec fields: opportunity country, study file and source

Additive only. New nullable columns so the running platform and its data are
untouched:

* `opportunities.country` — «الدولة *» on the new-opportunity modal (Table 5).
* `opportunities.attachment_file_id` — the optional study file (Table 5).
* `opportunities.source` — where the opportunity came from, e.g. the website
  (Table 3).

Revision ID: b5e6f7a8c9d0
Revises: a4d5e6f7b8c9
Create Date: 2026-11-17 11:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b5e6f7a8c9d0'
down_revision: Union[str, None] = 'a4d5e6f7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('opportunities', sa.Column('country', sa.String(length=64), nullable=True))
    op.add_column('opportunities', sa.Column('attachment_file_id', sa.Integer(), nullable=True))
    op.add_column('opportunities', sa.Column('source', sa.String(length=64), nullable=True))
    op.create_foreign_key(
        'fk_opportunities_attachment_file_id',
        'opportunities',
        'stored_files',
        ['attachment_file_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_opportunities_attachment_file_id', 'opportunities', type_='foreignkey')
    op.drop_column('opportunities', 'source')
    op.drop_column('opportunities', 'attachment_file_id')
    op.drop_column('opportunities', 'country')
