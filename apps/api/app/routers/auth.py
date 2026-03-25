"""
Auth router — JWT via httpOnly cookie + Bearer header fallback.

POST /api/v1/auth/register  → create tenant + workspace + super_admin → JWT + cookie
POST /api/v1/auth/login     → email + password → JWT + refresh_token cookies
GET  /api/v1/auth/me        → current user profile (requires JWT)
POST /api/v1/auth/refresh   → exchange refresh token for new access + refresh pair
POST /api/v1/auth/logout    → revoke access + refresh tokens, clear cookies
"""

import hashlib
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.core.exceptions import UnauthorizedError
from app.core.rate_limit import rate_limit
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
)
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.revoked_token_repository import RevokedTokenRepository
from app.repositories.tenant_repository import TenantRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserProfileResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_NAME = "access_token"
_REFRESH_COOKIE_NAME = "refresh_token"
_COOKIE_MAX_AGE = settings.jwt_access_token_expire_minutes * 60  # seconds
_REFRESH_MAX_AGE = 30 * 24 * 60 * 60  # 30 days in seconds
_REFRESH_EXPIRES_DELTA = timedelta(days=30)


def _auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(
        tenant_repo=TenantRepository(db),
        workspace_repo=WorkspaceRepository(db),
        user_repo=UserRepository(db),
    )


def _set_auth_cookie(response: Response, token: str) -> None:
    """Set httpOnly access_token cookie. secure=True in production."""
    response.set_cookie(
        key=_COOKIE_NAME,
        value=f"Bearer {token}",
        httponly=True,
        samesite="lax",
        max_age=_COOKIE_MAX_AGE,
        secure=settings.is_production,
        path="/",
    )


def _set_refresh_cookie(response: Response, token: str) -> None:
    """Set httpOnly refresh_token cookie scoped to /auth/refresh only."""
    response.set_cookie(
        key=_REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=_REFRESH_MAX_AGE,
        secure=settings.is_production,
        path="/api/v1/auth/refresh",
    )


async def _issue_refresh_token(
    user_id,
    response: Response,
    refresh_repo: RefreshTokenRepository,
) -> None:
    """Create a DB refresh token record and set the cookie."""
    raw, token_hash = create_refresh_token(user_id)
    expires_at = datetime.now(UTC) + _REFRESH_EXPIRES_DELTA
    await refresh_repo.create(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    _set_refresh_cookie(response, raw)


def _extract_token_from_request(request: Request) -> str | None:
    """Extract raw JWT from Authorization header or access_token cookie."""
    # 1. Bearer header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    # 2. Cookie
    cookie = request.cookies.get(_COOKIE_NAME, "")
    if cookie:
        return cookie.removeprefix("Bearer ").strip()
    return None


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    req: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    svc: AuthService = Depends(_auth_service),
    _: None = Depends(rate_limit(10, 60)),
) -> RegisterResponse:
    result = await svc.register(req)
    _set_auth_cookie(response, result.access_token)
    # Issue refresh token
    refresh_repo = RefreshTokenRepository(db)
    await _issue_refresh_token(result.user_id, response, refresh_repo)
    await db.commit()
    return result


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    svc: AuthService = Depends(_auth_service),
    _: None = Depends(rate_limit(20, 60)),
) -> TokenResponse:
    result = await svc.login(req)
    _set_auth_cookie(response, result.access_token)
    # Issue refresh token — need user ID from the login result
    # AuthService.login returns TokenResponse; fetch user for ID
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(req.email)
    if user:
        refresh_repo = RefreshTokenRepository(db)
        await _issue_refresh_token(user.id, response, refresh_repo)
        await db.commit()
    return result


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Exchange a valid refresh_token cookie for a new access + refresh token pair.
    Enforces rotation: old refresh token is revoked immediately.
    """
    raw_refresh = request.cookies.get(_REFRESH_COOKIE_NAME)
    if not raw_refresh:
        raise UnauthorizedError("No refresh token provided")

    token_hash = hashlib.sha256(raw_refresh.encode()).hexdigest()
    refresh_repo = RefreshTokenRepository(db)
    record = await refresh_repo.get_by_hash(token_hash)

    if record is None or record.is_revoked:
        raise UnauthorizedError("Refresh token is invalid or revoked")

    # Check expiry
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        raise UnauthorizedError("Refresh token has expired")

    # Rotate: revoke old token, issue new pair
    await refresh_repo.revoke(record.id)

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(record.user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    new_access = create_access_token(str(user.id))
    _set_auth_cookie(response, new_access)
    await _issue_refresh_token(user.id, response, refresh_repo)
    await db.commit()

    return TokenResponse(
        access_token=new_access,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserProfileResponse)
async def me(current_user: CurrentUserDep) -> UserProfileResponse:
    return UserProfileResponse.model_validate(current_user)


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Revoke the current access token JTI and all refresh tokens for the user.
    Clears both auth cookies.
    """
    token = _extract_token_from_request(request)
    if token:
        try:
            payload = decode_access_token(token)
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                from datetime import timezone
                expires_at = datetime.fromtimestamp(exp, tz=UTC)
                revoked_repo = RevokedTokenRepository(db)
                await revoked_repo.add(
                    jti=jti,
                    user_id=current_user.id,
                    expires_at=expires_at,
                )
        except Exception:
            pass  # Don't block logout on token decode errors

    # Revoke all refresh tokens for the user
    refresh_repo = RefreshTokenRepository(db)
    await refresh_repo.revoke_all_for_user(current_user.id)
    await db.commit()

    # Clear cookies
    response.delete_cookie(key=_COOKIE_NAME, path="/", samesite="lax")
    response.delete_cookie(
        key=_REFRESH_COOKIE_NAME, path="/api/v1/auth/refresh", samesite="lax"
    )
    return None
