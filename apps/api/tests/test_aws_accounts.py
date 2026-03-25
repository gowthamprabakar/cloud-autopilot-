"""
AWS Account tests — Phase 3.

Strategy:
- HTTP-level tests mock StsClient at the job import level (not aiobotocore).
- The Security Hub check in AwsAccountValidateJob is non-fatal (any error → warn).
- The SecurityHubSyncJob.run() is mocked for the /sync endpoint test.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.integrations.aws.sts_client import AssumedRoleCredentials
from app.jobs.base import JobResult, JobStatus

REGISTER_PAYLOAD = {
    "tenant_name": "Ops Corp",
    "tenant_slug": "ops-corp",
    "workspace_name": "Production",
    "email": "ops@example.com",
    "password": "securepw123",
    "full_name": "Ops Admin",
    "plan": "baseline",
}

VALID_ACCOUNT = {
    "account_id": "123456789012",
    "account_alias": "production-aws",
    "role_arn": "arn:aws:iam::123456789012:role/CloudPostureCopilot",
    "external_id": "ext-abc-123",
}

_MOCK_CREDS = AssumedRoleCredentials(
    access_key_id="ASIATESTING",
    secret_access_key="fakesecret",
    session_token="faketoken",
    assumed_role_arn="arn:aws:sts::123456789012:assumed-role/CloudPostureCopilot/test",
    expiration="2099-01-01T00:00:00+00:00",
)
_MOCK_IDENTITY = {
    "Account": "123456789012",
    "Arn": "arn:aws:sts::123456789012:assumed-role/CloudPostureCopilot/test",
    "UserId": "AROA123456:test",
}


async def _get_token(client: AsyncClient) -> str:
    res = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert res.status_code == 201, res.text
    return res.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _mock_sts():
    """Patch StsClient.from_settings() so assume_role + get_caller_identity succeed."""
    inst = MagicMock()
    inst.assume_role = AsyncMock(return_value=_MOCK_CREDS)
    inst.get_caller_identity = AsyncMock(return_value=_MOCK_IDENTITY)
    return patch(
        "app.jobs.aws_account_validate_job.StsClient.from_settings",
        return_value=inst,
    )


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_accounts_empty(client: AsyncClient):
    token = await _get_token(client)
    res = await client.get("/api/v1/aws-accounts", headers=_auth(token))
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.asyncio
async def test_create_account_returns_201_and_validates(client: AsyncClient):
    # STS mocked → validate job completes → account ACTIVE
    with _mock_sts():
        token = await _get_token(client)
        res = await client.post(
            "/api/v1/aws-accounts", json=VALID_ACCOUNT, headers=_auth(token)
        )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["account_id"] == "123456789012"
    assert data["account_alias"] == "production-aws"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_create_account_duplicate_returns_409(client: AsyncClient):
    token = await _get_token(client)
    await client.post("/api/v1/aws-accounts", json=VALID_ACCOUNT, headers=_auth(token))
    res = await client.post(
        "/api/v1/aws-accounts", json=VALID_ACCOUNT, headers=_auth(token)
    )
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_create_account_invalid_account_id_returns_422(client: AsyncClient):
    token = await _get_token(client)
    bad = {**VALID_ACCOUNT, "account_id": "12345"}
    res = await client.post("/api/v1/aws-accounts", json=bad, headers=_auth(token))
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_create_account_invalid_role_arn_returns_422(client: AsyncClient):
    token = await _get_token(client)
    bad = {**VALID_ACCOUNT, "role_arn": "not-a-valid-arn"}
    res = await client.post("/api/v1/aws-accounts", json=bad, headers=_auth(token))
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_get_account(client: AsyncClient):
    token = await _get_token(client)
    create_res = await client.post(
        "/api/v1/aws-accounts", json=VALID_ACCOUNT, headers=_auth(token)
    )
    account_id = create_res.json()["id"]
    res = await client.get(f"/api/v1/aws-accounts/{account_id}", headers=_auth(token))
    assert res.status_code == 200
    assert res.json()["id"] == account_id


@pytest.mark.asyncio
async def test_update_account_alias(client: AsyncClient):
    token = await _get_token(client)
    create_res = await client.post(
        "/api/v1/aws-accounts", json=VALID_ACCOUNT, headers=_auth(token)
    )
    account_id = create_res.json()["id"]
    res = await client.patch(
        f"/api/v1/aws-accounts/{account_id}",
        json={"account_alias": "updated-alias"},
        headers=_auth(token),
    )
    assert res.status_code == 200
    assert res.json()["account_alias"] == "updated-alias"


@pytest.mark.asyncio
async def test_delete_account(client: AsyncClient):
    token = await _get_token(client)
    create_res = await client.post(
        "/api/v1/aws-accounts", json=VALID_ACCOUNT, headers=_auth(token)
    )
    account_id = create_res.json()["id"]
    res = await client.delete(
        f"/api/v1/aws-accounts/{account_id}", headers=_auth(token)
    )
    assert res.status_code == 204
    get_res = await client.get(
        f"/api/v1/aws-accounts/{account_id}", headers=_auth(token)
    )
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_list_job_runs_after_create(client: AsyncClient):
    with _mock_sts():
        token = await _get_token(client)
        create_res = await client.post(
            "/api/v1/aws-accounts", json=VALID_ACCOUNT, headers=_auth(token)
        )
        account_id = create_res.json()["id"]
        res = await client.get(
            f"/api/v1/aws-accounts/{account_id}/job-runs", headers=_auth(token)
        )
    assert res.status_code == 200
    runs = res.json()
    assert len(runs) == 1
    run = runs[0]
    assert run["job_type"] == "aws_account_validate"
    assert run["status"] == "completed"
    assert "steps" in run["progress_detail"]


@pytest.mark.asyncio
async def test_trigger_sync_requires_active_account(client: AsyncClient):
    """Sync on non-ACTIVE account returns 409."""
    # No STS mock → validation fails → account = ERROR
    token = await _get_token(client)
    create_res = await client.post(
        "/api/v1/aws-accounts", json=VALID_ACCOUNT, headers=_auth(token)
    )
    account_id = create_res.json()["id"]
    res = await client.post(
        f"/api/v1/aws-accounts/{account_id}/sync", headers=_auth(token)
    )
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_trigger_sync_active_account_returns_202(client: AsyncClient):
    """Sync on ACTIVE account returns 202 + job_run body."""
    # Phase 1: create & validate account (mock STS so it goes ACTIVE)
    with _mock_sts():
        token = await _get_token(client)
        create_res = await client.post(
            "/api/v1/aws-accounts", json=VALID_ACCOUNT, headers=_auth(token)
        )
        account_id = create_res.json()["id"]
        assert create_res.json()["status"] == "active"

    # Phase 2: trigger sync — mock SecurityHubSyncJob.run to avoid real AWS calls
    _completed = JobResult(
        status=JobStatus.COMPLETED,
        message="Sync complete",
        output={"findings_ingested": 0, "findings_skipped": 0, "normalization": {}, "error": None},
    )
    with patch(
        "app.jobs.security_hub_sync_job.SecurityHubSyncJob.run",
        new=AsyncMock(return_value=_completed),
    ):
        res = await client.post(
            f"/api/v1/aws-accounts/{account_id}/sync", headers=_auth(token)
        )

    assert res.status_code == 202, res.text
    body = res.json()
    assert body["job_type"] == "security_hub_sync"
    assert body["status"] == "completed"


@pytest.mark.asyncio
async def test_list_accounts_no_auth_returns_401(client: AsyncClient):
    res = await client.get("/api/v1/aws-accounts")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_create_account_no_auth_returns_401(client: AsyncClient):
    res = await client.post("/api/v1/aws-accounts", json=VALID_ACCOUNT)
    assert res.status_code == 401
