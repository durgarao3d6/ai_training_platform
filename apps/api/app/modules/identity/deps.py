"""Request dependencies: current principal, permission checks, RLS-scoped DB session.

Human review required (tech lead).
"""

import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.modules.identity.permissions import Permission, has_any
from app.modules.identity.security import TokenError, decode_access_token

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    user_id: uuid.UUID
    roles: frozenset[str]


def get_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> Principal:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    try:
        claims = decode_access_token(credentials.credentials, settings)
        roles = claims.get("roles", [])
        if not isinstance(roles, list):
            raise TokenError("bad roles claim")
        return Principal(
            user_id=uuid.UUID(str(claims["sub"])), roles=frozenset(str(r) for r in roles)
        )
    except (TokenError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired or invalid") from exc


def require_permission(*required: Permission) -> Callable[[Principal], Principal]:
    """Allow the request if the principal holds ANY of the given permissions; otherwise 403."""

    def check(principal: Principal = Depends(get_principal)) -> Principal:
        if not has_any(principal.roles, *required):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have access to this.")
        return principal

    return check


def set_rls_context(db: DbSession, principal: Principal) -> None:
    """Transaction-local settings read by the RLS policies. Lost on commit (fails closed)."""
    db.execute(
        text("SELECT set_config('app.user_id', :uid, true), set_config('app.roles', :roles, true)"),
        {"uid": str(principal.user_id), "roles": ",".join(sorted(principal.roles))},
    )


def get_scoped_db(
    principal: Principal = Depends(get_principal), db: DbSession = Depends(get_db)
) -> Iterator[DbSession]:
    """DB session with RLS context set. Use this in every authenticated endpoint."""
    set_rls_context(db, principal)
    yield db
