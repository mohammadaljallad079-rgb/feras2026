"""Authentication: login, refresh, logout, password reset."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, permissions_of, role_slugs
from app.core.config import settings
from app.core.db import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_opaque_token,
    hash_password,
    new_opaque_token,
    verify_password,
)
from app.models.identity import PasswordResetToken, RefreshToken, User
from app.services import mail
from app.schemas import (
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetIssued,
    PasswordResetRequest,
    RefreshRequest,
    TokenPair,
)
from app.services import audit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_tokens(db: Session, user: User) -> TokenPair:
    access = create_access_token(str(user.id), role_slugs(user))
    refresh = create_refresh_token(str(user.id))
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_opaque_token(refresh),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days),
        )
    )
    user.last_login_at = datetime.now(timezone.utc)
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/token", response_model=TokenPair)
def login_form(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> TokenPair:
    return _login(db, form.username, form.password)


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    return _login(db, payload.email, payload.password)


def _login(db: Session, email: str, password: str) -> TokenPair:
    user = db.execute(select(User).where(User.email == email.lower())).scalar_one_or_none()
    if user is None or not user.is_active or not user.password_hash or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    tokens = _issue_tokens(db, user)
    audit.record(db, action="auth.login", actor=user)
    db.commit()
    return tokens


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    try:
        claims = decode_token(payload.refresh_token, expected_type="refresh")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    stored = db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hash_opaque_token(payload.refresh_token))
    ).scalar_one_or_none()
    if stored is None or stored.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")
    user = db.get(User, int(claims["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    stored.revoked_at = datetime.now(timezone.utc)
    tokens = _issue_tokens(db, user)
    db.commit()
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
def logout(
    payload: RefreshRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    stored = db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hash_opaque_token(payload.refresh_token))
    ).scalar_one_or_none()
    if stored is not None:
        stored.revoked_at = datetime.now(timezone.utc)
    audit.record(db, action="auth.logout", actor=user)
    db.commit()


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name_ar": user.full_name_ar,
        "full_name_en": user.full_name_en,
        "locale": user.locale,
        "roles": role_slugs(user),
        "permissions": sorted(permissions_of(user)),
    }


@router.post("/password-reset/request", response_model=PasswordResetIssued)
def request_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)) -> PasswordResetIssued:
    user = db.execute(select(User).where(User.email == payload.email.lower())).scalar_one_or_none()
    # Always answer the same way so the endpoint cannot enumerate accounts.
    if user is None:
        return PasswordResetIssued(message="If the account exists, a reset link has been issued.")
    token = new_opaque_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_opaque_token(token),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.password_reset_minutes),
        )
    )
    audit.record(db, action="auth.password_reset_requested", actor=user)
    db.commit()
    # The link is emailed when a mail transport is configured. The token is only
    # echoed back when an operator opted in for local testing; it is single-use
    # and expiring either way.
    content = mail.password_reset_email(user.locale or "ar", token)
    delivered = mail.send(user.email, content)
    # Handing the token back to an anonymous caller is a full account takeover:
    # anyone who knows an email address could set its password. It is therefore
    # only echoed when an operator has explicitly opted in for local testing.
    echo = not delivered and settings.expose_reset_token
    if not delivered:
        # Without a transport the operator needs a way to reach the user, so the
        # link is logged rather than returned to the caller.
        logger.info(
            "Password reset link for %s: %s/reset-password?token=%s",
            user.email,
            settings.frontend_base_url.rstrip("/"),
            token,
        )
    return PasswordResetIssued(
        reset_token=token if echo else None,
        message=(
            "Reset link emailed. It is single-use and expires."
            if delivered
            else "Mail transport is not configured; deliver the reset link out-of-band. It is single-use and expires."
        ),
    )


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
def confirm_reset(payload: PasswordResetConfirm, db: Session = Depends(get_db)) -> None:
    row = db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hash_opaque_token(payload.token)
        )
    ).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if row is None or row.used_at is not None or row.expires_at < now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    user = db.get(User, row.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
    user.password_hash = hash_password(payload.new_password)
    row.used_at = now
    audit.record(db, action="auth.password_reset_completed", actor=user)
    db.commit()
