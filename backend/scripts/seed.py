"""Seed the system roles and a set of demonstration accounts.

Demonstration accounts exist so the workflows can be exercised end to end. They
are *not* presented as real business data, and no company/report rows are
invented here: those are created through the application itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Run as `python scripts/seed.py`, so the package root is the parent directory
# rather than the script's own directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.api.v1.users import ensure_system_roles
from app.core.db import SessionLocal
from app.core.permissions import ROLE_TEMPLATES
from app.core.security import hash_password
from app.models.identity import Role, User, UserRole

DEMO_PASSWORD = "Safir!2026"
DEMO_USERS = [
    ("owner@safir-platform.com", "مالك المجموعة", "Holding Owner", ["owner"]),
    ("manager@safir-platform.com", "مدير شركة", "Company Manager", ["company_manager"]),
    ("accountant@safir-platform.com", "محاسب المجموعة", "Holding Accountant", ["accountant"]),
    ("bd@safir-platform.com", "مطوّر أعمال", "Business Developer", ["business_developer"]),
    ("marketer@safir-platform.com", "مسوّق", "Marketer", ["marketer"]),
    ("designer@safir-platform.com", "مصمّم", "Designer", ["designer"]),
    ("advisor@safir-platform.com", "مستشار خارجي", "External Advisor", ["advisor"]),
    ("specialist@safir-platform.com", "أخصائي خدمات", "Service Specialist", ["service_specialist"]),
]


def main() -> int:
    db = SessionLocal()
    try:
        ensure_system_roles(db)
        for email, name_ar, name_en, slugs in DEMO_USERS:
            user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
            if user is None:
                user = User(
                    email=email,
                    full_name_ar=name_ar,
                    full_name_en=name_en,
                    locale="ar",
                    password_hash=hash_password(DEMO_PASSWORD),
                    is_active=True,
                )
                db.add(user)
                db.flush()
            else:
                user.password_hash = hash_password(DEMO_PASSWORD)
            existing = {ur.role.slug for ur in user.roles if ur.role}
            for slug in slugs:
                if slug in existing:
                    continue
                role = db.execute(select(Role).where(Role.slug == slug)).scalar_one()
                db.add(UserRole(user_id=user.id, role_id=role.id))
        db.commit()
        print(f"Seeded {len(ROLE_TEMPLATES)} system roles and {len(DEMO_USERS)} demo accounts.")
        print(f"Demo password: {DEMO_PASSWORD}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
