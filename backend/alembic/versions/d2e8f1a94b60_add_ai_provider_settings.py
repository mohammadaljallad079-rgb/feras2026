"""add AI provider settings table

Design reference page 17 specifies owner-only OpenAI settings: a hidden key, a
connection test and a model class. The key is stored server-side and never
returned by the API.

Revision ID: d2e8f1a94b60
Revises: c7a9e1b53d24
Create Date: 2026-11-16 12:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd2e8f1a94b60'
down_revision: Union[str, None] = 'c7a9e1b53d24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ai_provider_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('provider', sa.String(length=32), nullable=False, server_default='openai'),
        sa.Column('model', sa.String(length=64), nullable=False, server_default='gpt-4o-mini'),
        sa.Column('base_url', sa.String(length=255), nullable=False, server_default='https://api.openai.com/v1'),
        sa.Column('api_key_encrypted', sa.Text(), nullable=True),
        sa.Column('updated_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('ai_provider_settings')
