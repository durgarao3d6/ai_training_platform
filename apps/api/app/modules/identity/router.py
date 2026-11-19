"""Auth endpoints (Architecture 14): login, refresh, logout, me. Human review required (tech lead).

- Access token: short-lived JWT returned in the body, sent as a Bearer header.
- Refresh token: opaque, rotated on every use, in an httpOnly Secure SameSite=Strict cookie
  scoped to the auth path.
- CSRF: double-submit. Cookie-authenticated calls (refresh, logout) must send X-CSRF-Token
  equal to the readable aitms_csrf cookie.
- Rate limiting per client IP on auth endpoints; lockout per account in the service.
"""

from datetime import datetime

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session as DbSession

from app.core.config import Settings, get_settings
from app.core.rate_limit import Limiter, get_limiter
from app.db.session import get_db
from app.modules.identity import security, service
from app.modules.identity.deps import Principal, get_principal

REFRESH_COOKIE = "aitms_refresh"
CSRF_COOKIE = "aitms_csrf"
AUTH_PATH = "/api/v1/auth"
GENERIC_LOGIN_ERROR = "Email or password is incorrect, or the account is temporarily locked."

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    roles: list[str]


class MeResponse(BaseModel):
    id: str
    email: str
    full_name: str
    roles: list[str]


def rate_limited(
    request: Request,
    limiter: Limiter = Depends(get_limiter),
    settings: Settings = Depends(get_settings),
) -> None:
    client = request.client.host if request.client else "unknown"
    if not limiter.hit(f"auth:{client}", settings.auth_rate_limit_per_minute, 60):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts. Wait a minute and try again."
        )


def require_csrf(
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> None:
    if not csrf_cookie or not csrf_header or not security.tokens_match(csrf_cookie, csrf_header):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Missing or invalid CSRF token")


def _set_session_cookies(
    response: Response, issued: service.IssuedTokens, settings: Settings
) -> None:
    max_age = int(
        (issued.refresh_expires_at - datetime.now(issued.refresh_expires_at.tzinfo)).total_seconds()
    )
    response.set_cookie(
        REFRESH_COOKIE,
        issued.refresh_token,
        max_age=max_age,
        path=AUTH_PATH,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
    )
    response.set_cookie(
        CSRF_COOKIE,
        security.new_opaque_token(),
        max_age=max_age,
        path="/",
        httponly=False,
        secure=settings.cookie_secure,
        samesite="strict",
    )


def _clear_session_cookies(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path=AUTH_PATH)
    response.delete_cookie(CSRF_COOKIE, path="/")


def _token_body(issued: service.IssuedTokens, settings: Settings) -> TokenResponse:
    return TokenResponse(
        access_token=issued.access_token,
        expires_in=settings.access_token_ttl_minutes * 60,
        roles=issued.roles,
    )


@router.post("/auth/login", response_model=TokenResponse, dependencies=[Depends(rate_limited)])
def login(
    body: LoginRequest,
    response: Response,
    db: DbSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    try:
        issued = service.login(db, body.email, body.password, settings)
    except service.AuthError as exc:
        db.commit()  # keep the failed-attempt counter even though we return an error
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, GENERIC_LOGIN_ERROR) from exc
    _set_session_cookies(response, issued, settings)
    return _token_body(issued, settings)


@router.post(
    "/auth/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limited), Depends(require_csrf)],
)
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
    db: DbSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    if not refresh_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    try:
        issued = service.refresh(db, refresh_token, settings)
    except service.AuthError as exc:
        db.commit()  # keep revocations made on token reuse
        _clear_session_cookies(response)
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Session expired. Sign in again."
        ) from exc
    _set_session_cookies(response, issued, settings)
    return _token_body(issued, settings)


@router.post(
    "/auth/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_csrf)]
)
def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
    db: DbSession = Depends(get_db),
) -> Response:
    if refresh_token:
        service.logout(db, refresh_token)
    response.status_code = status.HTTP_204_NO_CONTENT
    _clear_session_cookies(response)
    return response


@router.get("/me", response_model=MeResponse)
def me(
    principal: Principal = Depends(get_principal), db: DbSession = Depends(get_db)
) -> MeResponse:
    user = service.get_user(db, principal.user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired or invalid")
    return MeResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        roles=service.roles_for(db, user.id),
    )
