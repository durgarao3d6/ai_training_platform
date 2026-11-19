"""Identity service: login with lockout, refresh rotation, logout. Human review required (tech lead).

Other modules use this interface, never the identity tables directly.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.config import Settings
from app.modules.identity import security
from app.modules.identity.models import RoleAssignment, Session, User


class AuthError(Exception):
    """Generic failure. The message never says whether the email exists."""


class AccountLocked(AuthError):
    pass


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    refresh_token: str
    refresh_expires_at: datetime
    user_id: uuid.UUID
    roles: list[str]


def roles_for(db: DbSession, user_id: uuid.UUID) -> list[str]:
    rows = db.scalars(select(RoleAssignment.role).where(RoleAssignment.user_id == user_id))
    return sorted(r.value for r in rows)


def _issue(db: DbSession, user: User, settings: Settings) -> IssuedTokens:
    roles = roles_for(db, user.id)
    refresh = security.new_opaque_token()
    expires = datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days)
    db.add(
        Session(
            user_id=user.id, refresh_token_hash=security.hash_token(refresh), expires_at=expires
        )
    )
    db.flush()
    return IssuedTokens(
        access_token=security.create_access_token(user.id, roles, settings),
        refresh_token=refresh,
        refresh_expires_at=expires,
        user_id=user.id,
        roles=roles,
    )


def login(db: DbSession, email: str, password: str, settings: Settings) -> IssuedTokens:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    now = datetime.now(UTC)

    if user is not None and user.locked_until is not None and user.locked_until > now:
        security.verify_password(None, password)  # keep timing uniform
        raise AccountLocked("account temporarily locked")

    if user is None or not security.verify_password(user.password_hash, password):
        if user is not None:
            user.failed_login_count += 1
            if user.failed_login_count >= settings.login_max_failures:
                user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
                user.failed_login_count = 0
            db.flush()
        raise AuthError("invalid credentials")

    user.failed_login_count = 0
    user.locked_until = None
    return _issue(db, user, settings)


def refresh(db: DbSession, refresh_token: str, settings: Settings) -> IssuedTokens:
    """Rotate: the presented refresh token is revoked and a new one issued.

    Reuse of a revoked token revokes every session of that user (likely theft).
    """
    now = datetime.now(UTC)
    session = db.scalar(
        select(Session).where(Session.refresh_token_hash == security.hash_token(refresh_token))
    )
    if session is None:
        raise AuthError("invalid refresh token")
    if session.revoked_at is not None:
        for other in db.scalars(
            select(Session).where(Session.user_id == session.user_id, Session.revoked_at.is_(None))
        ):
            other.revoked_at = now
        db.flush()
        raise AuthError("refresh token reused")
    if session.expires_at <= now:
        raise AuthError("refresh token expired")

    session.revoked_at = now
    user = db.get(User, session.user_id)
    if user is None:
        raise AuthError("invalid refresh token")
    return _issue(db, user, settings)


def logout(db: DbSession, refresh_token: str) -> None:
    session = db.scalar(
        select(Session).where(Session.refresh_token_hash == security.hash_token(refresh_token))
    )
    if session is not None and session.revoked_at is None:
        session.revoked_at = datetime.now(UTC)
        db.flush()


def get_user(db: DbSession, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)
