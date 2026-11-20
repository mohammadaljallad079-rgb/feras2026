"""slide eyebrow: per-slide tag line above the headline

The Word spec gives each hero slide its own tag (for example «ستارت أب سفير
القابضة · البحرين» on the first, «شركات المجموعة» on the second). The slider
rendered one hard-coded tag for every slide, so the copy could not match the
spec without a column. Nullable, so existing rows and the running site are
untouched until the owner edits a slide.

Revision ID: c4a7b21e9d63
Revises: b7c1f4d92e35
Create Date: 2026-11-20 05:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c4a7b21e9d63'
down_revision: Union[str, None] = 'b7c1f4d92e35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('site_slides', sa.Column('eyebrow_ar', sa.String(length=120), nullable=True))
    op.add_column('site_slides', sa.Column('eyebrow_en', sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column('site_slides', 'eyebrow_en')
    op.drop_column('site_slides', 'eyebrow_ar')
