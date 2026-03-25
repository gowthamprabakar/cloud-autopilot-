"""
Inspector sync tests — Sprint 6.

Strategy:
- HTTP-level tests mock StsClient at the job import level (same pattern as test_aws_accounts.py).
- InspectorClient.iter_active_findings is mocked to return empty or fixture data.
- Tests cover: auth, account existence, status gating, 202 response,
  job_run record creation, multi-region payload propagation, and
  enabled_regions create/update.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.integrations.aws.sts_client import AssumedRoleCredentials
from app.jobs.base import JobResult, JobStatus

# ── Fixtures ────────────────────────────────────────────────────────────────

REGISTER_PAYLOAD = {
    "tenant_name": "Inspector Corp",
    "tenant_slug": "inspector-corp",
    "workspace_name": "Production",
    "email": "inspector@example.com",
    "password": "securepw456",
    "full_name": "Inspector Admin",
    "plan": "baseline",
}

VALID_ACCOUNT = {
    "account_id": "111122223333",
    "account_alias": "inspector-aws",
    "role_arn": "arn:aws:iam::111122223333:role/CloudPostureCopilot",
    "external_id": "ext-insp-001",
}

VALID_ACCOUNT_MULTI_REGION = {
    "account_id": "444455556666",
    "account_alias": "multi-region-aws",
    "role_arn": "arn:aws:iam::444455556666:role/CloudPostureCopilot",
    "external_id": "ext-multi-001",
    "enabled_regions": ["us-east-1", "us-west-2", "eu-west-1"],
}

_MOCK_CREDS = AssumedRoleCredentials(
    access_key_id="ASIATESTING123",
    secret_access_key="fakesecretkey",
    session_token="faketoken456",
    assumed_role_arn="arn:aws:sts::111122223333:assumed-role/CloudPostureCopilot/test",
    expiration="2099-01-01T00:00:00+00:00",
)
_MOCK_IDENTITY = {
    "Account": "111122223333",
    "Arn": "arn:aws:sts::111122223333:assumed-role/CloudPostureCopilot/test",
    "UserId": "AROA999888:test",
}


# ── Helpers ─────────────────────────────────────────────────────────────────

async def _get_token(client: AsyncClient) -> str:
    res = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert res.status_code == 201, res.text
    return res.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _mock_sts_validate(account_id: str = "111122223333"):
    """
    Patch StsClient so AWS account validation succeeds.
    account_id must match the payload's account_id — the validation job
    compares GetCallerIdentity["Account"] against the expected account number.
    """
    identity = {**_MOCK_IDENTITY, "Account": account_id}
    inst = MagicMock()
    inst.assume_role = AsyncMock(return_value=_MOCK_CREDS)
    inst.get_caller_identity = AsyncMock(return_value=identity)
    return patch(
        "app.jobs.aws_account_validate_job.StsClient.from_settings",
        return_value=inst,
    )


def _mock_inspector_job_empty():
    """Mock InspectorSyncJob.run to return COMPLETED with zero findings."""
    completed = JobResult(
        status=JobStatus.COMPLETED,
        message="Inspector sync complete: 0 ingested, 0 skipped, 1 region(s)",
        output={
            "regions_processed": [{"region": "us-east-1", "ingested": 0}],
            "findings_ingested": 0,
            "findings_skipped": 0,
            "normalization": {},
            "error": None,
        },
    )
    return patch(
        "app.jobs.inspector_sync_job.InspectorSyncJob.run",
        new=AsyncMock(return_value=completed),
    )


async def _create_active_account(
    client: AsyncClient,
    token: str,
    account_payload: dict | None = None,
) -> str:
    """Create an account and get it to ACTIVE status via mocked STS."""
    payload = account_payload or VALID_ACCOUNT
    # Pass the payload's account_id so GetCallerIdentity returns the right account.
    with _mock_sts_validate(account_id=payload["account_id"]):
        res = await client.post(
            "/api/v1/aws-accounts", json=payload, headers=_auth(token)
        )
    assert res.status_code == 201, res.text
    assert res.json()["status"] == "active"
    return res.json()["id"]


# ── Tests: Inspector sync endpoint auth and status gating ───────────────────

@pytest.mark.asyncio
async def test_inspector_sync_no_auth_returns_401(client: AsyncClient):
    """Inspector sync endpoint requires authentication."""
    fake_id = str(uuid.uuid4())
    res = await client.post(f"/api/v1/aws-accounts/{fake_id}/sync/inspector")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_inspector_sync_nonexistent_account_returns_404(client: AsyncClient):
    """Inspector sync on an account that does not exist returns 404."""
    token = await _get_token(client)
    fake_id = str(uuid.uuid4())
    res = await client.post(
        f"/api/v1/aws-accounts/{fake_id}/sync/inspector",
        headers=_auth(token),
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_inspector_sync_non_active_account_returns_409(client: AsyncClient):
    """Inspector sync on a non-ACTIVE account returns 409."""
    # Do NOT mock STS → validation fails → account stays in ERROR
    token = await _get_token(client)
    create_res = await client.post(
        "/api/v1/aws-accounts", json=VALID_ACCOUNT, headers=_auth(token)
    )
    assert create_res.status_code == 201
    account_id = create_res.json()["id"]
    # Account should be in ERROR (STS not mocked → validation failed)
    assert create_res.json()["status"] != "active"

    res = await client.post(
        f"/api/v1/aws-accounts/{account_id}/sync/inspector",
        headers=_auth(token),
    )
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_inspector_sync_active_account_returns_202(client: AsyncClient):
    """Inspector sync on an ACTIVE account returns 202 with a JobRun body."""
    token = await _get_token(client)
    account_id = await _create_active_account(client, token)

    with _mock_inspector_job_empty():
        res = await client.post(
            f"/api/v1/aws-accounts/{account_id}/sync/inspector",
            headers=_auth(token),
        )

    assert res.status_code == 202, res.text
    body = res.json()
    assert body["job_type"] == "inspector_sync"
    assert body["status"] == "completed"


@pytest.mark.asyncio
async def test_inspector_sync_returns_job_run_record(client: AsyncClient):
    """Inspector sync response is a valid JobRun schema."""
    token = await _get_token(client)
    account_id = await _create_active_account(client, token)

    with _mock_inspector_job_empty():
        res = await client.post(
            f"/api/v1/aws-accounts/{account_id}/sync/inspector",
            headers=_auth(token),
        )

    assert res.status_code == 202, res.text
    body = res.json()
    # Validate required JobRun fields are present
    assert "id" in body
    assert "aws_account_id" in body
    assert "workspace_id" in body
    assert "job_type" in body
    assert "status" in body
    assert "progress_detail" in body
    assert body["job_type"] == "inspector_sync"
    assert uuid.UUID(body["id"])  # valid UUID
    assert uuid.UUID(body["aws_account_id"]) == uuid.UUID(account_id)


@pytest.mark.asyncio
async def test_inspector_sync_job_run_appears_in_list(client: AsyncClient):
    """After inspector sync, the job_run appears in the account's job-runs list."""
    token = await _get_token(client)
    account_id = await _create_active_account(client, token)

    with _mock_inspector_job_empty():
        sync_res = await client.post(
            f"/api/v1/aws-accounts/{account_id}/sync/inspector",
            headers=_auth(token),
        )
    assert sync_res.status_code == 202

    list_res = await client.get(
        f"/api/v1/aws-accounts/{account_id}/job-runs",
        headers=_auth(token),
    )
    assert list_res.status_code == 200
    runs = list_res.json()
    job_types = [r["job_type"] for r in runs]
    assert "inspector_sync" in job_types


@pytest.mark.asyncio
async def test_inspector_sync_multi_region_payload_propagated(client: AsyncClient):
    """
    When an account has multiple enabled_regions, the inspector sync job
    receives the full regions list in the payload.
    """
    token = await _get_token(client)
    account_id = await _create_active_account(
        client, token, account_payload=VALID_ACCOUNT_MULTI_REGION
    )

    captured_payload: dict = {}

    original_run = None

    async def _capture_run(self) -> JobResult:
        nonlocal captured_payload
        captured_payload = dict(self.ctx.payload)
        return JobResult(
            status=JobStatus.COMPLETED,
            message="Inspector sync complete: 0 ingested, 0 skipped, 3 region(s)",
            output={
                "regions_processed": [],
                "findings_ingested": 0,
                "findings_skipped": 0,
                "normalization": {},
                "error": None,
            },
        )

    with patch(
        "app.jobs.inspector_sync_job.InspectorSyncJob.run",
        new=_capture_run,
    ):
        res = await client.post(
            f"/api/v1/aws-accounts/{account_id}/sync/inspector",
            headers=_auth(token),
        )

    assert res.status_code == 202, res.text
    assert "regions" in captured_payload
    assert set(captured_payload["regions"]) == {"us-east-1", "us-west-2", "eu-west-1"}


# ── Tests: enabled_regions on create/update ─────────────────────────────────

@pytest.mark.asyncio
async def test_create_account_default_enabled_regions(client: AsyncClient):
    """Account created without enabled_regions defaults to ['us-east-1']."""
    token = await _get_token(client)
    res = await client.post(
        "/api/v1/aws-accounts", json=VALID_ACCOUNT, headers=_auth(token)
    )
    assert res.status_code == 201, res.text
    assert res.json()["enabled_regions"] == ["us-east-1"]


@pytest.mark.asyncio
async def test_create_account_with_custom_enabled_regions(client: AsyncClient):
    """Account created with explicit enabled_regions stores the list correctly."""
    token = await _get_token(client)
    res = await client.post(
        "/api/v1/aws-accounts",
        json=VALID_ACCOUNT_MULTI_REGION,
        headers=_auth(token),
    )
    assert res.status_code == 201, res.text
    stored_regions = res.json()["enabled_regions"]
    assert set(stored_regions) == {"us-east-1", "us-west-2", "eu-west-1"}


@pytest.mark.asyncio
async def test_create_account_invalid_region_returns_422(client: AsyncClient):
    """Account creation with an unknown region name returns 422."""
    token = await _get_token(client)
    bad_payload = {**VALID_ACCOUNT, "enabled_regions": ["us-east-1", "mars-south-1"]}
    res = await client.post(
        "/api/v1/aws-accounts", json=bad_payload, headers=_auth(token)
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_create_account_empty_regions_returns_422(client: AsyncClient):
    """Account creation with an empty enabled_regions list returns 422."""
    token = await _get_token(client)
    bad_payload = {**VALID_ACCOUNT, "enabled_regions": []}
    res = await client.post(
        "/api/v1/aws-accounts", json=bad_payload, headers=_auth(token)
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_patch_account_updates_enabled_regions(client: AsyncClient):
    """PATCH /aws-accounts/{id} can update enabled_regions."""
    token = await _get_token(client)
    create_res = await client.post(
        "/api/v1/aws-accounts", json=VALID_ACCOUNT, headers=_auth(token)
    )
    assert create_res.status_code == 201
    account_id = create_res.json()["id"]
    assert create_res.json()["enabled_regions"] == ["us-east-1"]

    patch_res = await client.patch(
        f"/api/v1/aws-accounts/{account_id}",
        json={"enabled_regions": ["us-east-1", "eu-central-1"]},
        headers=_auth(token),
    )
    assert patch_res.status_code == 200
    updated_regions = patch_res.json()["enabled_regions"]
    assert set(updated_regions) == {"us-east-1", "eu-central-1"}


@pytest.mark.asyncio
async def test_patch_account_invalid_regions_returns_422(client: AsyncClient):
    """PATCH with an invalid region name in enabled_regions returns 422."""
    token = await _get_token(client)
    create_res = await client.post(
        "/api/v1/aws-accounts", json=VALID_ACCOUNT, headers=_auth(token)
    )
    account_id = create_res.json()["id"]

    res = await client.patch(
        f"/api/v1/aws-accounts/{account_id}",
        json={"enabled_regions": ["not-a-region"]},
        headers=_auth(token),
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_patch_account_empty_regions_returns_422(client: AsyncClient):
    """PATCH with empty enabled_regions returns 422."""
    token = await _get_token(client)
    create_res = await client.post(
        "/api/v1/aws-accounts", json=VALID_ACCOUNT, headers=_auth(token)
    )
    account_id = create_res.json()["id"]

    res = await client.patch(
        f"/api/v1/aws-accounts/{account_id}",
        json={"enabled_regions": []},
        headers=_auth(token),
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_inspector_sync_sts_failure_marks_job_failed(client: AsyncClient):
    """
    If the InspectorSyncJob fails (e.g. STS error), the job_run status is
    'failed' and the endpoint still returns 202 (job was accepted and ran).
    """
    token = await _get_token(client)
    account_id = await _create_active_account(client, token)

    failed = JobResult(
        status=JobStatus.FAILED,
        error="AssumeRole failed (AccessDenied): not authorized",
        output={
            "regions_processed": [],
            "findings_ingested": 0,
            "findings_skipped": 0,
            "normalization": {},
            "error": "AssumeRole failed (AccessDenied): not authorized",
        },
    )
    with patch(
        "app.jobs.inspector_sync_job.InspectorSyncJob.run",
        new=AsyncMock(return_value=failed),
    ):
        res = await client.post(
            f"/api/v1/aws-accounts/{account_id}/sync/inspector",
            headers=_auth(token),
        )

    assert res.status_code == 202, res.text
    body = res.json()
    assert body["job_type"] == "inspector_sync"
    assert body["status"] == "failed"
