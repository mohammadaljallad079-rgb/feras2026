"""Authentication / authorization dependencies.

These are the single enforcement point for RBAC and company isolation. A hidden
button in the UI is never sufficient; every protected route passes through here.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_token
from app.models.identity import User, UserCompany, UserRole
from app.services import audit

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_error
    try:
        payload = decode_token(token, expected_type="access")
    except JWTError:
        raise credentials_error
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise credentials_error
    return user


def permissions_of(user: User) -> set[str]:
    perms: set[str] = set()
    for ur in user.roles:
        if ur.role:
            perms |= ur.role.permission_codes
    return perms


def role_slugs(user: User) -> list[str]:
    return sorted(ur.role.slug for ur in user.roles if ur.role)


def _record_denial(db: Session, user: User, missing: list[str]) -> None:
    """§11: «فتح رابط غير مصرح به يرفض ويسجل» — the refusal itself is the event."""
    audit.record(
        db,
        action="security.access_denied",
        actor=user,
        target_type="permission",
        target_id=",".join(missing),
        meta={"missing_permissions": missing},
    )
    db.commit()


def require(*required: str) -> Callable[[User], User]:
    """Dependency factory: caller must hold *all* listed permissions."""

    def _checker(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        held = permissions_of(user)
        missing = [p for p in required if p not in held]
        if missing:
            _record_denial(db, user, missing)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "forbidden", "missing_permissions": missing},
            )
        return user

    return _checker


def require_any(*required: str) -> Callable[[User], User]:
    """Dependency factory: caller must hold *at least one* of the permissions.

    Used where a screen is reachable by different duties — the report list, for
    instance, is read by a manager (``report:view_own``) and by the accountant
    and owner (``report:view_all``).
    """

    def _checker(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        held = permissions_of(user)
        if not any(p in held for p in required):
            _record_denial(db, user, list(required))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "forbidden", "missing_permissions": list(required)},
            )
        return user

    return _checker


def holding_company_id(db: Session) -> int | None:
    """The id of the Holding's own company record, if it exists.

    §7.1: the Holding keeps its own monthly report alongside the subsidiaries,
    and §7.4 gives it its own report fields. It is a company row so those fields
    and the report can hang on it, but it is not a subsidiary.
    """
    from app.models.business import Company

    return db.execute(select(Company.id).where(Company.is_holding.is_(True))).scalars().first()


def allowed_company_ids(db: Session, user: User) -> set[int] | None:
    """Return the set of companies a user may access, or ``None`` for all.

    The owner role has holding-wide oversight; every other user is limited to
    the companies explicitly granted to them plus any company-scoped role.

    The accountant and the business developer are holding-level roles: §7.1 makes
    the developer the author of the Holding's own report and §5.3 makes the
    accountant the reviewer of every report, the Holding's included. They are
    therefore granted the Holding's record (if it exists) so the Holding report
    flow works, without gaining access to any subsidiary they were not granted.
    """
    if "owner" in role_slugs(user):
        return None
    rows = db.execute(
        select(UserCompany.company_id).where(UserCompany.user_id == user.id)
    ).scalars().all()
    scoped = {r.company_id for r in user.roles if r.company_id is not None}
    allowed = set(rows) | scoped
    slugs = role_slugs(user)
    if "accountant" in slugs or "business_developer" in slugs:
        holding_id = holding_company_id(db)
        if holding_id is not None:
            allowed.add(holding_id)
    return allowed


def assert_company_access(db: Session, user: User, company_id: int) -> None:
    allowed = allowed_company_ids(db, user)
    if allowed is None:
        return
    if company_id not in allowed:
        # The brief (§11, Table 3) requires a refused cross-company access to be
        # recorded: "opening an unauthorised link is refused and logged". The
        # attempt is committed before the 404 is raised so the audit survives.
        audit.record(
            db,
            action="security.access_denied",
            actor=user,
            target_type="company",
            target_id=company_id,
            company_id=company_id,
        )
        db.commit()
        # 404 rather than 403 so the response does not confirm that another
        # company exists. The body still says `denied` so the interface can show
        # the 403 state (design p.4) instead of a generic "not found".
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "reason": "denied"},
        )


def has_any_role(user: User, *slugs: str) -> bool:
    return bool(set(role_slugs(user)) & set(slugs))
