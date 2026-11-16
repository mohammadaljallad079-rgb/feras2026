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


def require(*required: str) -> Callable[[User], User]:
    """Dependency factory: caller must hold *all* listed permissions."""

    def _checker(user: User = Depends(get_current_user)) -> User:
        held = permissions_of(user)
        missing = [p for p in required if p not in held]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "forbidden", "missing_permissions": missing},
            )
        return user

    return _checker


def allowed_company_ids(db: Session, user: User) -> set[int] | None:
    """Return the set of companies a user may access, or ``None`` for all.

    The owner role has holding-wide oversight; every other user is limited to
    the companies explicitly granted to them plus any company-scoped role.
    """
    if "owner" in role_slugs(user):
        return None
    rows = db.execute(
        select(UserCompany.company_id).where(UserCompany.user_id == user.id)
    ).scalars().all()
    scoped = {r.company_id for r in user.roles if r.company_id is not None}
    ids = set(rows) | scoped
    return ids


def assert_company_access(db: Session, user: User, company_id: int) -> None:
    allowed = allowed_company_ids(db, user)
    if allowed is None:
        return
    if company_id not in allowed:
        # 404 rather than 403: do not confirm the existence of other companies.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def has_any_role(user: User, *slugs: str) -> bool:
    return bool(set(role_slugs(user)) & set(slugs))
