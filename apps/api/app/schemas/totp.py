from pydantic import BaseModel
from typing import Optional


class TotpSetupResponse(BaseModel):
    secret: str          # plaintext secret (shown once for manual entry)
    otpauth_uri: str     # otpauth:// URI for QR code
    backup_codes: list[str]  # shown once


class TotpVerifyRequest(BaseModel):
    code: str            # 6-digit TOTP code


class TotpVerifyResponse(BaseModel):
    enabled: bool
    message: str


class TotpDisableRequest(BaseModel):
    code: str            # current TOTP code to confirm


class TotpStatusResponse(BaseModel):
    enabled: bool
    pending: bool


class TotpConfirmRequest(BaseModel):
    temp_token: str      # from login step 1
    code: str            # TOTP or backup code


class LoginStep1Response(BaseModel):
    requires_2fa: bool = True
    temp_token: str      # short-lived JWT with claim "2fa_pending": true
