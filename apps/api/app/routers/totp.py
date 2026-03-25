"""TOTP 2FA endpoints."""
import json
from datetime import datetime, timedelta, UTC

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.deps import get_current_user, get_db
from app.core.exceptions import BadRequestError, UnauthorizedError
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.totp import (
    TotpSetupResponse, TotpVerifyRequest, TotpVerifyResponse,
    TotpDisableRequest, TotpStatusResponse,
)
from app.services.totp_service import (
    generate_totp_secret, encrypt_secret, decrypt_secret,
    get_totp_uri, verify_totp_code,
    generate_backup_codes, verify_backup_code,
)

router = APIRouter(prefix="/auth/2fa", tags=["2fa"])


@router.get("/status", response_model=TotpStatusResponse)
async def get_2fa_status(current_user: User = Depends(get_current_user)):
    return TotpStatusResponse(
        enabled=current_user.totp_enabled,
        pending=current_user.totp_pending,
    )


@router.post("/setup", response_model=TotpSetupResponse)
async def setup_2fa(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate TOTP secret and QR URI. Does NOT activate 2FA yet (must call /verify)."""
    if current_user.totp_enabled:
        raise BadRequestError("2FA is already enabled. Disable it first.")

    secret = generate_totp_secret()
    encrypted = encrypt_secret(secret)
    plaintext_codes, hashed_codes = generate_backup_codes()

    current_user.totp_secret = encrypted
    current_user.totp_pending = True
    current_user.totp_backup_codes = json.dumps(hashed_codes)
    current_user.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(current_user)

    uri = get_totp_uri(secret, current_user.email)
    return TotpSetupResponse(
        secret=secret,
        otpauth_uri=uri,
        backup_codes=plaintext_codes,
    )


@router.post("/verify", response_model=TotpVerifyResponse)
async def verify_and_activate_2fa(
    body: TotpVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify TOTP code and activate 2FA."""
    if current_user.totp_enabled:
        raise BadRequestError("2FA is already active.")
    if not current_user.totp_secret or not current_user.totp_pending:
        raise BadRequestError("Run /auth/2fa/setup first.")

    if not verify_totp_code(current_user.totp_secret, body.code):
        raise UnauthorizedError("Invalid TOTP code.")

    current_user.totp_enabled = True
    current_user.totp_pending = False
    current_user.updated_at = datetime.now(UTC)
    await db.commit()

    return TotpVerifyResponse(enabled=True, message="2FA activated successfully.")


@router.post("/disable", response_model=TotpVerifyResponse)
async def disable_2fa(
    body: TotpDisableRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disable 2FA. Requires current TOTP code to confirm."""
    if not current_user.totp_enabled:
        raise BadRequestError("2FA is not enabled.")

    if not verify_totp_code(current_user.totp_secret, body.code):
        raise UnauthorizedError("Invalid TOTP code.")

    current_user.totp_enabled = False
    current_user.totp_pending = False
    current_user.totp_secret = None
    current_user.totp_backup_codes = None
    current_user.updated_at = datetime.now(UTC)
    await db.commit()

    return TotpVerifyResponse(enabled=False, message="2FA disabled.")
