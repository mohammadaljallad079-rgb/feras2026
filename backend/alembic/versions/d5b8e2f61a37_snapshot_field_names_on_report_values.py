"""Snapshot the field names on report values

§6.4 Table 6: "Editing does not change past reports". The value row already kept
the definition version, but the labels were still read live from the field, so
renaming a field rewrote the heading of every historical report. Store the names
as they were at capture time and backfill from the current definition.

Revision ID: d5b8e2f61a37
Revises: c4a7b21e9d63
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "d5b8e2f61a37"
down_revision: Union[str, None] = "c4a7b21e9d63"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column("report_values", sa.Column("field_name_ar", sa.String(255), nullable=True))
    op.add_column("report_values", sa.Column("field_name_en", sa.String(255), nullable=True))
    # Existing rows predate the snapshot; the definition they were captured
    # under is the best available label, and it is frozen from here on.
    op.execute(
        """
        UPDATE report_values AS rv
        SET field_name_ar = ff.name_ar,
            field_name_en = ff.name_en
        FROM form_fields AS ff
        WHERE ff.id = rv.field_id
        """
    )


def downgrade() -> None:
    op.drop_column("report_values", "field_name_en")
    op.drop_column("report_values", "field_name_ar")
