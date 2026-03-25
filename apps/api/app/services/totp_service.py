"""TOTP service using pyotp + Fernet encryption for secret storage."""
import json
import secrets
import hashlib
import pyotp
from cryptography.fernet import Fernet
from app.core.config import settings


def _get_fernet() -> Fernet:
    """Get Fernet instance using a key derived from SECRET_KEY."""
    import base64
    key_bytes = hashlib.sha256(settings.secret_key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def generate_totp_secret() -> str:
    """Generate a new TOTP secret (base32)."""
    return pyotp.random_base32()


def encrypt_secret(secret: str) -> str:
    """Encrypt TOTP secret for storage."""
    f = _get_fernet()
    return f.encrypt(secret.encode()).decode()


def decrypt_secret(encrypted: str) -> str:
    """Decrypt stored TOTP secret."""
    f = _get_fernet()
    return f.decrypt(encrypted.encode()).decode()


def get_totp_uri(secret: str, email: str, issuer: str = "Cloud Posture Copilot") -> str:
    """Get otpauth:// URI for QR code generation."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)


def verify_totp_code(encrypted_secret: str, code: str) -> bool:
    """Verify a 6-digit TOTP code. Accepts current and ±1 window."""
    try:
        secret = decrypt_secret(encrypted_secret)
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)
    except Exception:
        return False


def generate_backup_codes(count: int = 8) -> tuple[list[str], list[str]]:
    """Generate backup codes. Returns (plaintext_list, hashed_list)."""
    codes = [secrets.token_hex(5).upper() for _ in range(count)]  # e.g. "A1B2C3D4E5"
    hashed = [hashlib.sha256(c.encode()).hexdigest() for c in codes]
    return codes, hashed


def verify_backup_code(stored_hashed_json: str, code: str) -> tuple[bool, str]:
    """
    Check if code matches any stored backup code.
    Returns (valid, updated_json_with_code_removed).
    """
    try:
        hashed_codes: list[str] = json.loads(stored_hashed_json)
        code_hash = hashlib.sha256(code.upper().encode()).hexdigest()
        if code_hash in hashed_codes:
            hashed_codes.remove(code_hash)
            return True, json.dumps(hashed_codes)
        return False, stored_hashed_json
    except Exception:
        return False, stored_hashed_json
