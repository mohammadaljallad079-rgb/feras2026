"""Seed the public-website CMS content from the brief-approved copy.

Idempotent: rows are matched by key/slug and updated, never duplicated. This
seeds *content structure and approved copy only* — no company, report, or
financial row is invented. Copy the missing `content-ar.md` / `content-en.md`
would have supplied is left null and flagged `needs_review` for the owner.

    DATABASE_URL=... python scripts/seed_site.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.content import site_content as content
from app.core.db import SessionLocal
from app.models.site import SiteNavLink, SiteSection, SiteService, SiteSetting, SiteSlide


def main() -> int:
    db = SessionLocal()
    try:
        # Settings
        for key, (ar, en) in content.SETTINGS.items():
            row = db.execute(select(SiteSetting).where(SiteSetting.key == key)).scalar_one_or_none()
            if row is None:
                db.add(SiteSetting(key=key, value_ar=ar, value_en=en))
            else:
                row.value_ar, row.value_en = ar, en

        # Hero slides (matched by order)
        existing_slides = {
            s.sort_order: s
            for s in db.execute(select(SiteSlide).order_by(SiteSlide.sort_order)).scalars().all()
        }
        for i, spec in enumerate(content.SLIDES):
            row = existing_slides.get(i)
            if row is None:
                db.add(SiteSlide(sort_order=i, **spec))
            else:
                for k, v in spec.items():
                    setattr(row, k, v)

        # Sections
        for spec in content.SECTIONS:
            row = db.execute(
                select(SiteSection).where(SiteSection.key == spec["key"])
            ).scalar_one_or_none()
            if row is None:
                db.add(SiteSection(**spec))
            else:
                for k, v in spec.items():
                    setattr(row, k, v)

        # Services
        for i, (slug, ar, en) in enumerate(content.SERVICES):
            row = db.execute(select(SiteService).where(SiteService.slug == slug)).scalar_one_or_none()
            if row is None:
                db.add(
                    SiteService(
                        slug=slug, name_ar=ar, name_en=en, sort_order=i, needs_review=True
                    )
                )
            else:
                row.name_ar, row.name_en, row.sort_order = ar, en, i

        # Navigation (header + footer)
        for location, links in (("header", content.HEADER_NAV), ("footer", content.FOOTER_NAV)):
            existing = {
                n.href: n
                for n in db.execute(
                    select(SiteNavLink).where(SiteNavLink.location == location)
                ).scalars().all()
            }
            for i, (ar, en, href) in enumerate(links):
                row = existing.get(href)
                if row is None:
                    db.add(
                        SiteNavLink(
                            location=location,
                            label_ar=ar,
                            label_en=en,
                            href=href,
                            sort_order=i,
                        )
                    )
                else:
                    row.label_ar, row.label_en, row.sort_order = ar, en, i
            # The brief's menu is a fixed set, so a link the seed no longer names
            # is removed rather than left behind from an earlier revision.
            wanted = {href for _, _, href in links}
            for href, row in existing.items():
                if href not in wanted:
                    db.delete(row)

        db.commit()
        print("Seeded website CMS content (settings, slides, sections, services, nav).")
        print("Copy still needing owner review is flagged needs_review in the CMS.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
