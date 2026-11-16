"""Users, roles, invitations and permission assignment."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require, require_any
from app.core.config import settings
from app.core.db import get_db
from app.core.permissions import ALL_PERMISSIONS, ROLE_TEMPLATES
from app.core.security import hash_opaque_token, new_opaque_token
from app.models.identity import (
    PasswordResetToken,
    Role,
    RolePermission,
    User,
    UserCompany,
    UserRole,
)
from app.schemas import (
    RoleCreate,
    RoleOut,
    RoleUpdate,
    UserCreate,
    UserDirectoryOut,
    UserInviteResult,
    UserOut,
    UserUpdate,
)
from app.services import audit

router = APIRouter(tags=["users"])


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name_ar=user.full_name_ar,
        full_name_en=user.full_name_en,
        locale=user.locale,
        is_active=user.is_active,
        roles=sorted(ur.role.slug for ur in user.roles if ur.role),
        company_ids=sorted(c.company_id for c in user.company_scopes),
        last_login_at=user.last_login_at,
    )


def _role_out(role: Role) -> RoleOut:
    return RoleOut(
        id=role.id,
        slug=role.slug,
        name_ar=role.name_ar,
        name_en=role.name_en,
        is_system=role.is_system,
        permission_codes=sorted(role.permission_codes),
    )


def ensure_system_roles(db: Session) -> None:
    """Idempotently create the built-in roles and reconcile their grants.

    A system role's grants are defined by ``ROLE_TEMPLATES``, so the set is
    reconciled exactly: a permission removed from the template is revoked here
    too. Otherwise a change to a role's duties in code would leave stale grants
    in the database and the two would disagree. Custom roles (``is_system``
    false) are never touched.
    """
    for slug, tpl in ROLE_TEMPLATES.items():
        role = db.execute(select(Role).where(Role.slug == slug)).scalar_one_or_none()
        if role is None:
            role = Role(slug=slug, name_ar=tpl["name_ar"], name_en=tpl["name_en"], is_system=True)
            db.add(role)
            db.flush()
        want = set(tpl["permissions"])  # type: ignore[arg-type]
        have = {p.permission for p in role.permissions}
        for perm in want - have:
            db.add(RolePermission(role_id=role.id, permission=perm))
        for grant in [p for p in role.permissions if p.permission not in want]:
            db.delete(grant)
    db.commit()


@router.get("/permissions")
def list_permissions(_: User = Depends(require("role:manage"))) -> dict:
    return {"permissions": list(ALL_PERMISSIONS)}


@router.get("/roles", response_model=list[RoleOut])
def list_roles(_: User = Depends(require("user:view")), db: Session = Depends(get_db)) -> list[RoleOut]:
    roles = db.execute(select(Role).order_by(Role.id)).scalars().all()
    return [_role_out(r) for r in roles]


@router.post("/roles", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreate,
    actor: User = Depends(require("role:manage")),
    db: Session = Depends(get_db),
) -> RoleOut:
    if db.execute(select(Role).where(Role.slug == payload.slug)).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role slug already exists")
    unknown = set(payload.permissions) - set(ALL_PERMISSIONS)
    if unknown:
        raise HTTPException(status_code=422, detail={"error": "unknown_permissions", "values": sorted(unknown)})
    role = Role(slug=payload.slug, name_ar=payload.name_ar, name_en=payload.name_en, is_system=False)
    db.add(role)
    db.flush()
    for perm in set(payload.permissions):
        db.add(RolePermission(role_id=role.id, permission=perm))
    audit.record(db, action="role.create", actor=actor, target_type="role", target_id=role.id)
    db.commit()
    db.refresh(role)
    return _role_out(role)


@router.patch("/roles/{role_id}", response_model=RoleOut)
def update_role(
    role_id: int,
    payload: RoleUpdate,
    actor: User = Depends(require("role:manage")),
    db: Session = Depends(get_db),
) -> RoleOut:
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    if payload.name_ar is not None:
        role.name_ar = payload.name_ar
    if payload.name_en is not None:
        role.name_en = payload.name_en
    if payload.permissions is not None:
        if role.is_system:
            raise HTTPException(status_code=400, detail="System roles cannot be re-scoped")
        unknown = set(payload.permissions) - set(ALL_PERMISSIONS)
        if unknown:
            raise HTTPException(status_code=422, detail={"error": "unknown_permissions", "values": sorted(unknown)})
        for existing in list(role.permissions):
            db.delete(existing)
        db.flush()
        for perm in set(payload.permissions):
            db.add(RolePermission(role_id=role.id, permission=perm))
    audit.record(db, action="role.update", actor=actor, target_type="role", target_id=role.id)
    db.commit()
    db.refresh(role)
    return _role_out(role)


@router.get("/users/directory", response_model=list[UserDirectoryOut])
def user_directory(
    _: User = Depends(
        require_any(
            "user:view", "directive:view", "lead:view", "service:view", "advisor:view"
        )
    ),
    db: Session = Depends(get_db),
) -> list[UserDirectoryOut]:
    """Active colleagues for recipient/assignee pickers.

    Declared before ``/users/{user_id}`` so the literal path wins the match.
    """
    users = (
        db.execute(select(User).where(User.is_active.is_(True)).order_by(User.id))
        .scalars()
        .all()
    )
    return [
        UserDirectoryOut(id=u.id, full_name_ar=u.full_name_ar, full_name_en=u.full_name_en)
        for u in users
    ]


@router.get("/users", response_model=list[UserOut])
def list_users(_: User = Depends(require("user:view")), db: Session = Depends(get_db)) -> list[UserOut]:
    users = db.execute(select(User).order_by(User.id)).scalars().all()
    return [_user_out(u) for u in users]


def _apply_assignments(db: Session, user: User, role_slugs: list[str], company_ids: list[int]) -> None:
    roles = db.execute(select(Role).where(Role.slug.in_(role_slugs))).scalars().all() if role_slugs else []
    found = {r.slug for r in roles}
    missing = set(role_slugs) - found
    if missing:
        raise HTTPException(status_code=422, detail={"error": "unknown_roles", "values": sorted(missing)})
    for existing in list(user.roles):
        db.delete(existing)
    db.flush()
    for role in roles:
        db.add(UserRole(user_id=user.id, role_id=role.id))
    for existing in list(user.company_scopes):
        db.delete(existing)
    db.flush()
    for cid in company_ids:
        db.add(UserCompany(user_id=user.id, company_id=cid))


@router.post("/users", response_model=UserInviteResult, status_code=status.HTTP_201_CREATED)
def invite_user(
    payload: UserCreate,
    actor: User = Depends(require("user:manage")),
    db: Session = Depends(get_db),
) -> UserInviteResult:
    if db.execute(select(User).where(User.email == payload.email.lower())).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(
        email=payload.email.lower(),
        full_name_ar=payload.full_name_ar,
        full_name_en=payload.full_name_en,
        locale=payload.locale,
        password_hash=None,
    )
    db.add(user)
    db.flush()
    _apply_assignments(db, user, payload.role_slugs, payload.company_ids)
    # Invitation issues a single-use setup link. No plain-text password is ever emailed.
    token = new_opaque_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_opaque_token(token),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.password_reset_minutes),
        )
    )
    audit.record(db, action="user.invite", actor=actor, target_type="user", target_id=user.id)
    db.commit()
    db.refresh(user)
    return UserInviteResult(
        user=_user_out(user),
        setup_token=token,
        setup_url=f"/{payload.locale}/set-password?token={token}",
    )


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    actor: User = Depends(require("user:manage")),
    db: Session = Depends(get_db),
) -> UserOut:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.full_name_ar is not None:
        user.full_name_ar = payload.full_name_ar
    if payload.full_name_en is not None:
        user.full_name_en = payload.full_name_en
    if payload.locale is not None:
        user.locale = payload.locale
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.role_slugs is not None or payload.company_ids is not None:
        _apply_assignments(
            db,
            user,
            payload.role_slugs if payload.role_slugs is not None else [ur.role.slug for ur in user.roles],
            payload.company_ids if payload.company_ids is not None else [c.company_id for c in user.company_scopes],
        )
    audit.record(db, action="user.update", actor=actor, target_type="user", target_id=user.id)
    db.commit()
    db.refresh(user)
    return _user_out(user)
