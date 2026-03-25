"""Tests for TOTP 2FA endpoints."""
import json
import pytest
import pyotp
from httpx import AsyncClient

from app.services.totp_service import (
    generate_totp_secret, encrypt_secret, decrypt_secret,
    get_totp_uri, verify_totp_code, generate_backup_codes, verify_backup_code,
)


# --- Unit tests for totp_service ---

def test_generate_and_encrypt_decrypt():
    secret = generate_totp_secret()
    assert len(secret) >= 16
    encrypted = encrypt_secret(secret)
    assert encrypted != secret
    assert decrypt_secret(encrypted) == secret


def test_verify_totp_code_valid():
    secret = generate_totp_secret()
    encrypted = encrypt_secret(secret)
    totp = pyotp.TOTP(secret)
    code = totp.now()
    assert verify_totp_code(encrypted, code) is True


def test_verify_totp_code_invalid():
    secret = generate_totp_secret()
    encrypted = encrypt_secret(secret)
    assert verify_totp_code(encrypted, "000000") is False


def test_get_totp_uri():
    secret = generate_totp_secret()
    uri = get_totp_uri(secret, "user@example.com")
    assert uri.startswith("otpauth://totp/")
    assert "user%40example.com" in uri or "user@example.com" in uri


def test_backup_codes_generated_and_verified():
    codes, hashed = generate_backup_codes(count=4)
    assert len(codes) == 4
    assert len(hashed) == 4
    stored = json.dumps(hashed)
    valid, updated = verify_backup_code(stored, codes[0])
    assert valid is True
    remaining = json.loads(updated)
    assert len(remaining) == 3


# --- API endpoint tests ---

@pytest.mark.asyncio
async def test_get_2fa_status(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/auth/2fa/status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is False
    assert data["pending"] is False


@pytest.mark.asyncio
async def test_setup_2fa_returns_secret_and_uri(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/v1/auth/2fa/setup", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "secret" in data
    assert data["otpauth_uri"].startswith("otpauth://totp/")
    assert len(data["backup_codes"]) == 8


@pytest.mark.asyncio
async def test_verify_activates_2fa(client: AsyncClient, auth_headers: dict):
    # Setup
    setup_resp = await client.post("/api/v1/auth/2fa/setup", headers=auth_headers)
    assert setup_resp.status_code == 200
    secret = setup_resp.json()["secret"]

    # Verify with correct code
    totp = pyotp.TOTP(secret)
    verify_resp = await client.post(
        "/api/v1/auth/2fa/verify",
        json={"code": totp.now()},
        headers=auth_headers,
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["enabled"] is True


@pytest.mark.asyncio
async def test_verify_wrong_code_rejected(client: AsyncClient, auth_headers: dict):
    await client.post("/api/v1/auth/2fa/setup", headers=auth_headers)
    resp = await client.post(
        "/api/v1/auth/2fa/verify",
        json={"code": "000000"},
        headers=auth_headers,
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_disable_2fa(client: AsyncClient, auth_headers: dict):
    # Setup + activate
    setup_resp = await client.post("/api/v1/auth/2fa/setup", headers=auth_headers)
    secret = setup_resp.json()["secret"]
    totp = pyotp.TOTP(secret)
    await client.post("/api/v1/auth/2fa/verify", json={"code": totp.now()}, headers=auth_headers)

    # Disable
    disable_resp = await client.post(
        "/api/v1/auth/2fa/disable",
        json={"code": totp.now()},
        headers=auth_headers,
    )
    assert disable_resp.status_code == 200
    assert disable_resp.json()["enabled"] is False


@pytest.mark.asyncio
async def test_setup_requires_auth(client: AsyncClient):
    resp = await client.post("/api/v1/auth/2fa/setup")
    assert resp.status_code == 401
