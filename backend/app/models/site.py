"""Public-website content: settings, sections, hero slides, services, navigation.

The public site and the admin CMS read and write these tables, so content edited
in the platform appears on the website with no deploy. Every row carries AR and
EN copy; `needs_review` marks copy that the owner has not yet approved, so
placeholder-free, approved text can be told apart from proposed text.
"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.identity import TimestampMixin


class SiteSetting(Base, TimestampMixin):
    """Key/value site settings (brand, contact, SEO, legal notice)."""

    __tablename__ = "site_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    value_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_en: Mapped[str | None] = mapped_column(Text, nullable=True)


class SiteSection(Base, TimestampMixin):
    """An ordered, toggleable homepage section with bilingual copy."""

    __tablename__ = "site_sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    title_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("stored_files.id", ondelete="SET NULL"), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)


class SiteSlide(Base, TimestampMixin):
    """A hero slide with bilingual copy and call-to-action buttons."""

    __tablename__ = "site_slides"

    id: Mapped[int] = mapped_column(primary_key=True)
    title_ar: Mapped[str] = mapped_column(Text)
    title_en: Mapped[str] = mapped_column(Text)
    body_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("stored_files.id", ondelete="SET NULL"), nullable=True
    )
    cta_primary_label_ar: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cta_primary_label_en: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cta_primary_href: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cta_secondary_label_ar: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cta_secondary_label_en: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cta_secondary_href: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class SiteService(Base, TimestampMixin):
    """An approved group service. Descriptions stay null until the owner adds them."""

    __tablename__ = "site_services"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name_ar: Mapped[str] = mapped_column(String(255))
    name_en: Mapped[str] = mapped_column(String(255))
    description_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)


class SiteNavLink(Base, TimestampMixin):
    """Header or footer navigation, bilingual label and href."""

    __tablename__ = "site_nav_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    location: Mapped[str] = mapped_column(String(16), index=True)  # header | footer
    label_ar: Mapped[str] = mapped_column(String(128))
    label_en: Mapped[str] = mapped_column(String(128))
    href: Mapped[str] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
