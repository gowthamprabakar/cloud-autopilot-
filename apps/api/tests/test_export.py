"""
CSV Export tests — GET /api/v1/findings/export

Strategy:
- HTTP-level tests with SQLite in-memory DB.
- Findings inserted directly via db_session fixture.
- CSV response parsed with Python's csv module.
"""

import csv
import io
import uuid

import pytest
from httpx import AsyncClient

from app.models.aws_account import AwsAccount
from app.models.canonical_finding import CanonicalFinding
from app.models.enums import (
    AwsAccountStatus,
    FindingSeverity,
    FindingSource,
    FindingStatus,
    TenantPlan,
    TenantStatus,
    WorkspaceStatus,
)
from app.models.tenant import Tenant
from app.models.workspace import Workspace

# ── Shared payloads ──────────────────────────────────────────────────────────

REGISTER_PAYLOAD = {
    "tenant_name": "Export Corp",
    "tenant_slug": "export-corp",
    "workspace_name": "Production",
    "email": "admin@export.example.com",
    "password": "securepw123",
    "full_name": "Export Admin",
    "plan": "baseline",
}

REGISTER_PAYLOAD_B = {
    "tenant_name": "Export Corp B",
    "tenant_slug": "export-corp-b",
    "workspace_name": "Production B",
    "email": "adminb@export.example.com",
    "password": "securepw123",
    "full_name": "Export Admin B",
    "plan": "baseline",
}


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _get_token(client: AsyncClient, payload: dict | None = None) -> str:
    p = payload or REGISTER_PAYLOAD
    res = await client.post("/api/v1/auth/register", json=p)
    assert res.status_code == 201, res.text
    return res.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _seed_finding(
    db,
    workspace_id: uuid.UUID,
    aws_account_id: uuid.UUID,
    *,
    severity: FindingSeverity = FindingSeverity.HIGH,
    status: FindingStatus = FindingStatus.OPEN,
    title: str = "Export Test Finding",
    risk_score: float = 7.5,
    compliance_frameworks: list[str] | None = None,
) -> CanonicalFinding:
    import hashlib
    fingerprint = hashlib.sha256(
        f"{workspace_id}:{aws_account_id}:{title}:{uuid.uuid4()}".encode()
    ).hexdigest()[:16]

    finding = CanonicalFinding(
        workspace_id=workspace_id,
        aws_account_id=aws_account_id,
        fingerprint=fingerprint,
        primary_source=FindingSource.SECURITY_HUB,
        severity=severity,
        status=status,
        risk_score=risk_score,
        title=title,
        description="Test description",
        remediation="Fix it",
        resource_arn="arn:aws:s3:::test-bucket",
        resource_type="AwsS3Bucket",
        region="us-east-1",
        compliance_frameworks=compliance_frameworks or [],
        tags={},
        first_seen_at="2024-01-01T00:00:00Z",
        last_seen_at="2024-01-02T00:00:00Z",
    )
    db.add(finding)
    await db.flush()
    await db.refresh(finding)
    return finding


async def _get_workspace_and_account(client, db, token, account_id: str) -> tuple[uuid.UUID, uuid.UUID]:
    """Get workspace_id from /me and create an aws account in it."""
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    assert me_res.status_code == 200
    workspace_id = uuid.UUID(me_res.json()["workspace_id"])

    acct = AwsAccount(
        workspace_id=workspace_id,
        account_id=account_id,
        role_arn=f"arn:aws:iam::{account_id}:role/TestRole",
        status=AwsAccountStatus.ACTIVE,
    )
    db.add(acct)
    await db.flush()
    return workspace_id, acct.id


# ── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_export_csv_returns_200_and_csv_content_type(client: AsyncClient):
    """GET /findings/export returns 200 with text/csv content type."""
    token = await _get_token(client)
    res = await client.get("/api/v1/findings/export", headers=_auth(token))
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]


@pytest.mark.asyncio
async def test_export_csv_has_header_row(client: AsyncClient):
    """CSV response includes expected header columns."""
    token = await _get_token(client)
    res = await client.get("/api/v1/findings/export", headers=_auth(token))
    assert res.status_code == 200

    reader = csv.DictReader(io.StringIO(res.text))
    expected_cols = {
        "id", "title", "severity", "status", "risk_score",
        "primary_source", "resource_type", "resource_arn", "region",
        "compliance_frameworks", "first_seen_at", "last_seen_at", "resolved_at",
        "aws_account_id",
    }
    assert expected_cols.issubset(set(reader.fieldnames or []))


@pytest.mark.asyncio
async def test_export_csv_includes_findings(client: AsyncClient, db_session):
    """Create 2 findings, export, check both rows are present in the CSV."""
    token = await _get_token(client)
    workspace_id, aws_account_id = await _get_workspace_and_account(
        client, db_session, token, "100200300400"
    )

    await _seed_finding(db_session, workspace_id, aws_account_id, title="Finding Alpha")
    await _seed_finding(db_session, workspace_id, aws_account_id, title="Finding Beta")
    await db_session.commit()

    res = await client.get("/api/v1/findings/export", headers=_auth(token))
    assert res.status_code == 200

    reader = csv.DictReader(io.StringIO(res.text))
    rows = list(reader)
    titles = {row["title"] for row in rows}
    assert "Finding Alpha" in titles
    assert "Finding Beta" in titles
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_export_csv_filters_by_severity(client: AsyncClient, db_session):
    """Create critical + high findings; export with severity=critical returns only 1 row."""
    token = await _get_token(client)
    workspace_id, aws_account_id = await _get_workspace_and_account(
        client, db_session, token, "100200300401"
    )

    await _seed_finding(
        db_session, workspace_id, aws_account_id,
        title="Critical Finding", severity=FindingSeverity.CRITICAL,
    )
    await _seed_finding(
        db_session, workspace_id, aws_account_id,
        title="High Finding", severity=FindingSeverity.HIGH,
    )
    await db_session.commit()

    res = await client.get(
        "/api/v1/findings/export?severity=critical", headers=_auth(token)
    )
    assert res.status_code == 200

    reader = csv.DictReader(io.StringIO(res.text))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["severity"] == "critical"
    assert rows[0]["title"] == "Critical Finding"


@pytest.mark.asyncio
async def test_export_requires_auth(client: AsyncClient):
    """GET /findings/export without a token returns 401."""
    res = await client.get("/api/v1/findings/export")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_export_workspace_isolation(client: AsyncClient, db_session):
    """User A's export does not contain User B's findings."""
    token_a = await _get_token(client, REGISTER_PAYLOAD)
    token_b = await _get_token(client, REGISTER_PAYLOAD_B)

    workspace_a, acct_a = await _get_workspace_and_account(
        client, db_session, token_a, "200300400500"
    )
    workspace_b, acct_b = await _get_workspace_and_account(
        client, db_session, token_b, "200300400501"
    )

    await _seed_finding(db_session, workspace_a, acct_a, title="User A Finding")
    await _seed_finding(db_session, workspace_b, acct_b, title="User B Finding")
    await db_session.commit()

    # User A export
    res_a = await client.get("/api/v1/findings/export", headers=_auth(token_a))
    assert res_a.status_code == 200
    rows_a = list(csv.DictReader(io.StringIO(res_a.text)))
    titles_a = {r["title"] for r in rows_a}
    assert "User A Finding" in titles_a
    assert "User B Finding" not in titles_a

    # User B export
    res_b = await client.get("/api/v1/findings/export", headers=_auth(token_b))
    assert res_b.status_code == 200
    rows_b = list(csv.DictReader(io.StringIO(res_b.text)))
    titles_b = {r["title"] for r in rows_b}
    assert "User B Finding" in titles_b
    assert "User A Finding" not in titles_b
