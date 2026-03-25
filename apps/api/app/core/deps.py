"""
FastAPI dependency injection wiring.

All shared dependencies live here:
- get_db        → AsyncSession (already in database.py — re-exported)
- get_current_user → authenticated User from JWT (cookie or bearer) or API key
- require_roles    → role-based access guard

Token extraction priority:
  1. Authorization: Bearer header (explicit — API clients, tests)
  2. access_token httpOnly cookie (browser clients set by /auth/login & /auth/register)

Bearer header takes priority so that explicit API credentials always win.
Browsers never send Authorization headers (they rely on cookies), so there
is no conflict in production. This ordering also prevents stale cookies from
shadowing explicitly-passed tokens in test clients that persist cookie jars.

API keys (sk- prefix) are also accepted as Bearer tokens for machine-to-machine
access without requiring JWT.
"""

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.revoked_token_repository import RevokedTokenRepository
from app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)

DbDep = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    db: DbDep,
) -> User:
    """
    Extract and validate JWT from Authorization header or httpOnly cookie.
    Bearer header takes priority so explicit API credentials always win.
    Cookie fallback serves browser clients that never send Authorization headers.

    Also accepts API keys (sk- prefix) as Bearer tokens for M2M access.
    """
    token: str | None = None

    # 1. Authorization: Bearer header (explicit — API clients and tests)
    if credentials is not None:
        token = credentials.credentials

    # 2. Fall back to httpOnly cookie (browser clients)
    if not token:
        cookie_value = request.cookies.get("access_token")
        if cookie_value:
            token = cookie_value.removeprefix("Bearer ").strip()

    if not token:
        raise UnauthorizedError("Missing authorization — provide cookie or Bearer header")

    # ── API Key path (sk- prefix) ──────────────────────────────────────────
    if token.startswith("sk-"):
        # Import here to avoid circular imports at module load time
        from app.repositories.api_key_repository import ApiKeyRepository

        key_hash = hashlib.sha256(token.encode()).hexdigest()
        api_key_repo = ApiKeyRepository(db)
        api_key = await api_key_repo.get_by_hash(key_hash)

        if api_key is None or not api_key.is_active:
            raise UnauthorizedError("Invalid or revoked API key")

        # Check expiry
        if api_key.expires_at is not None:
            exp = api_key.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=UTC)
            if exp < datetime.now(UTC):
                raise UnauthorizedError("API key has expired")

        # Update last_used_at (fire and forget — don't fail on error)
        try:
            await api_key_repo.touch_last_used(api_key.id)
            await db.commit()
        except Exception:
            pass

        # Return the user who created the key
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(api_key.created_by_user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("API key owner not found or inactive")
        return user

    # ── JWT path (existing logic) ──────────────────────────────────────────
    payload = decode_access_token(token)

    # Check blocklist — only if jti is present (backwards compat: tokens without jti still pass)
    jti = payload.get("jti")
    if jti:
        revoked_repo = RevokedTokenRepository(db)
        if await revoked_repo.is_revoked(jti):
            raise UnauthorizedError("Token has been revoked")

    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedError("Invalid token payload")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedError("Invalid token subject")

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    """Dependency factory — enforce minimum role."""

    async def _check(current_user: CurrentUserDep) -> User:
        if UserRole(current_user.role) not in roles:
            raise ForbiddenError(
                f"Requires one of: {[r.value for r in roles]}"
            )
        return current_user

    return Depends(_check)
