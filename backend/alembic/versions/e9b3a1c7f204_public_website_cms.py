"""public website CMS tables and submission inbox extensions

Additive only: new CMS tables (settings, sections, slides, services, nav), a
submission history table, and new nullable columns on `website_submissions`.
No existing column is dropped, renamed or retyped, so the running platform and
its data are untouched.

Revision ID: e9b3a1c7f204
Revises: d2e8f1a94b60
Create Date: 2026-11-17 07:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e9b3a1c7f204'
down_revision: Union[str, None] = 'd2e8f1a94b60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'site_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('key', sa.String(length=64), nullable=False),
        sa.Column('value_ar', sa.Text(), nullable=True),
        sa.Column('value_en', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_site_settings_key', 'site_settings', ['key'], unique=True)

    op.create_table(
        'site_sections',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('key', sa.String(length=64), nullable=False),
        sa.Column('title_ar', sa.Text(), nullable=True),
        sa.Column('title_en', sa.Text(), nullable=True),
        sa.Column('body_ar', sa.Text(), nullable=True),
        sa.Column('body_en', sa.Text(), nullable=True),
        sa.Column('image_file_id', sa.Integer(), sa.ForeignKey('stored_files.id', ondelete='SET NULL'), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_visible', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('needs_review', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_site_sections_key', 'site_sections', ['key'], unique=True)

    op.create_table(
        'site_slides',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title_ar', sa.Text(), nullable=False),
        sa.Column('title_en', sa.Text(), nullable=False),
        sa.Column('body_ar', sa.Text(), nullable=True),
        sa.Column('body_en', sa.Text(), nullable=True),
        sa.Column('image_file_id', sa.Integer(), sa.ForeignKey('stored_files.id', ondelete='SET NULL'), nullable=True),
        sa.Column('cta_primary_label_ar', sa.String(length=64), nullable=True),
        sa.Column('cta_primary_label_en', sa.String(length=64), nullable=True),
        sa.Column('cta_primary_href', sa.String(length=255), nullable=True),
        sa.Column('cta_secondary_label_ar', sa.String(length=64), nullable=True),
        sa.Column('cta_secondary_label_en', sa.String(length=64), nullable=True),
        sa.Column('cta_secondary_href', sa.String(length=255), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'site_services',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('slug', sa.String(length=64), nullable=False),
        sa.Column('name_ar', sa.String(length=255), nullable=False),
        sa.Column('name_en', sa.String(length=255), nullable=False),
        sa.Column('description_ar', sa.Text(), nullable=True),
        sa.Column('description_en', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(length=32), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('needs_review', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_site_services_slug', 'site_services', ['slug'], unique=True)

    op.create_table(
        'site_nav_links',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('location', sa.String(length=16), nullable=False),
        sa.Column('label_ar', sa.String(length=128), nullable=False),
        sa.Column('label_en', sa.String(length=128), nullable=False),
        sa.Column('href', sa.String(length=255), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_site_nav_links_location', 'site_nav_links', ['location'])

    # --- submission inbox extensions (all nullable / defaulted) -------------
    op.add_column('website_submissions', sa.Column('reference_no', sa.String(length=32), nullable=True))
    op.create_index('ix_website_submissions_reference_no', 'website_submissions', ['reference_no'], unique=True)
    op.add_column('website_submissions', sa.Column('service_type', sa.String(length=128), nullable=True))
    op.add_column('website_submissions', sa.Column('country', sa.String(length=64), nullable=True))
    op.add_column('website_submissions', sa.Column('subject', sa.String(length=255), nullable=True))
    op.add_column('website_submissions', sa.Column('expertise', sa.String(length=255), nullable=True))
    op.add_column('website_submissions', sa.Column('consent', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('website_submissions', sa.Column('attachment_file_id', sa.Integer(), sa.ForeignKey('stored_files.id', ondelete='SET NULL'), nullable=True))
    op.add_column('website_submissions', sa.Column('assigned_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True))
    op.create_index('ix_website_submissions_assigned_user_id', 'website_submissions', ['assigned_user_id'])
    op.add_column('website_submissions', sa.Column('internal_notes', sa.Text(), nullable=True))
    op.add_column('website_submissions', sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        'website_submission_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('submission_id', sa.Integer(), sa.ForeignKey('website_submissions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('actor_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('from_status', sa.String(length=16), nullable=True),
        sa.Column('to_status', sa.String(length=16), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_website_submission_events_submission_id', 'website_submission_events', ['submission_id'])


def downgrade() -> None:
    op.drop_index('ix_website_submission_events_submission_id', table_name='website_submission_events')
    op.drop_table('website_submission_events')

    op.drop_column('website_submissions', 'reviewed_at')
    op.drop_column('website_submissions', 'internal_notes')
    op.drop_index('ix_website_submissions_assigned_user_id', table_name='website_submissions')
    op.drop_column('website_submissions', 'assigned_user_id')
    op.drop_column('website_submissions', 'attachment_file_id')
    op.drop_column('website_submissions', 'consent')
    op.drop_column('website_submissions', 'expertise')
    op.drop_column('website_submissions', 'subject')
    op.drop_column('website_submissions', 'country')
    op.drop_column('website_submissions', 'service_type')
    op.drop_index('ix_website_submissions_reference_no', table_name='website_submissions')
    op.drop_column('website_submissions', 'reference_no')

    op.drop_index('ix_site_nav_links_location', table_name='site_nav_links')
    op.drop_table('site_nav_links')
    op.drop_index('ix_site_services_slug', table_name='site_services')
    op.drop_table('site_services')
    op.drop_table('site_slides')
    op.drop_index('ix_site_sections_key', table_name='site_sections')
    op.drop_table('site_sections')
    op.drop_index('ix_site_settings_key', table_name='site_settings')
    op.drop_table('site_settings')
