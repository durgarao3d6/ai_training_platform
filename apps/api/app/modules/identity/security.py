"""Password hashing and tokens (Architecture 13.1). Human review required (tech lead)."""

import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import Settings

_hasher = PasswordHasher()  # Argon2id with library defaults

# Verified against when the email is unknown, so timing does not reveal which emails exist.
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing")

MIN_SECRET_LENGTH = 32


class TokenError(Exception):
    pass


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def _secret(settings: Settings) -> str:
    if len(settings.jwt_secret) < MIN_SECRET_LENGTH:
        raise RuntimeError(f"JWT_SECRET must be set and at least {MIN_SECRET_LENGTH} characters")
    return settings.jwt_secret


def create_access_token(user_id: uuid.UUID, roles: list[str], settings: Settings) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "roles": roles,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
        "type": "access",
    }
    return jwt.encode(claims, _secret(settings), algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> dict[str, object]:
    try:
        claims: dict[str, object] = jwt.decode(
            token,
            _secret(settings),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError("invalid or expired token") from exc
    if claims.get("type") != "access":
        raise TokenError("wrong token type")
    return claims


def new_opaque_token() -> str:
    """Random token for refresh and CSRF values. Only its hash is stored."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def tokens_match(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())
