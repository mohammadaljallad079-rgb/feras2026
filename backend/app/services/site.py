"""Public-site content service: reads the CMS tables into one bootstrap payload.

The public site reads content through here, so a change made in the admin CMS is
visible on the website without a deploy. Only visible/active rows are returned.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.site_content import OPPORTUNITY_COUNTRIES, OPPORTUNITY_COUNTRIES_EN
from app.models.site import SiteNavLink, SiteSection, SiteService, SiteSetting, SiteSlide


def settings_map(db: Session) -> dict[str, dict[str, str | None]]:
    rows = db.execute(select(SiteSetting)).scalars().all()
    return {r.key: {"ar": r.value_ar, "en": r.value_en} for r in rows}


def visible_sections(db: Session) -> list[SiteSection]:
    return list(
        db.execute(
            select(SiteSection)
            .where(SiteSection.is_visible.is_(True))
            .order_by(SiteSection.sort_order, SiteSection.id)
        )
        .scalars()
        .all()
    )


def active_slides(db: Session) -> list[SiteSlide]:
    return list(
        db.execute(
            select(SiteSlide)
            .where(SiteSlide.is_active.is_(True))
            .order_by(SiteSlide.sort_order, SiteSlide.id)
        )
        .scalars()
        .all()
    )


def active_services(db: Session) -> list[SiteService]:
    return list(
        db.execute(
            select(SiteService)
            .where(SiteService.is_active.is_(True))
            .order_by(SiteService.sort_order, SiteService.id)
        )
        .scalars()
        .all()
    )


def nav_links(db: Session, location: str) -> list[SiteNavLink]:
    return list(
        db.execute(
            select(SiteNavLink)
            .where(SiteNavLink.location == location, SiteNavLink.is_active.is_(True))
            .order_by(SiteNavLink.sort_order, SiteNavLink.id)
        )
        .scalars()
        .all()
    )


def opportunity_countries() -> list[dict[str, str]]:
    return [
        {"ar": ar, "en": en}
        for ar, en in zip(OPPORTUNITY_COUNTRIES, OPPORTUNITY_COUNTRIES_EN, strict=True)
    ]
