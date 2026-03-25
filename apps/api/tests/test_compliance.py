"""
Compliance API tests — Phase 3.

Strategy:
- HTTP-level tests with SQLite in-memory DB.
- canonical findings with compliance_frameworks inserted via db_session.
"""

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
)

# ── Shared payloads ──────────────────────────────────────────────────────────

REGISTER_PAYLOAD = {
    "tenant_name": "Compliance Corp",
    "tenant_slug": "compliance-corp",
    "workspace_name": "Production",
    "email": "admin@compliance.example.com",
    "password": "securepw123",
    "full_name": "Compliance Admin",
    "plan": "baseline",
}


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _get_token(client: AsyncClient) -> str:
    res = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert res.status_code == 201, res.text
    return res.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _seed_aws_account(db, workspace_id: uuid.UUID, account_id: str = "112233445566") -> AwsAccount:
    acct = AwsAccount(
        workspace_id=workspace_id,
        account_id=account_id,
        role_arn=f"arn:aws:iam::{account_id}:role/TestRole",
        status=AwsAccountStatus.ACTIVE,
    )
    db.add(acct)
    await db.flush()
    return acct


async def _seed_canonical_finding(
    db,
    workspace_id: uuid.UUID,
    aws_account_id: uuid.UUID,
    *,
    title: str = "Compliance Finding",
    severity: FindingSeverity = FindingSeverity.HIGH,
    status: FindingStatus = FindingStatus.OPEN,
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
        risk_score=6.5,
        title=title,
        description=None,
        remediation=None,
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


# ── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_compliance_stats_no_auth(client: AsyncClient):
    res = await client.get("/api/v1/compliance/stats")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_compliance_stats_empty_workspace(client: AsyncClient):
    """No findings → returns empty frameworks list."""
    token = await _get_token(client)
    res = await client.get("/api/v1/compliance/stats", headers=_auth(token))
    assert res.status_code == 200
    body = res.json()
    assert body["frameworks"] == []
    assert body["last_updated"] is None


@pytest.mark.asyncio
async def test_compliance_stats_with_findings(client: AsyncClient, db_session):
    """Findings with compliance_frameworks → correct coverage stats returned."""
    token = await _get_token(client)
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    workspace_id = uuid.UUID(me_res.json()["workspace_id"])

    acct = await _seed_aws_account(db_session, workspace_id, "998877665544")

    # 2 open findings in CIS_AWS_1.4
    await _seed_canonical_finding(
        db_session, workspace_id, acct.id,
        title="CIS Finding 1",
        compliance_frameworks=["CIS_AWS_1.4"],
        status=FindingStatus.OPEN,
    )
    await _seed_canonical_finding(
        db_session, workspace_id, acct.id,
        title="CIS Finding 2",
        compliance_frameworks=["CIS_AWS_1.4"],
        status=FindingStatus.RESOLVED,
    )
    # 1 finding in PCI_DSS_3.2.1
    await _seed_canonical_finding(
        db_session, workspace_id, acct.id,
        title="PCI Finding 1",
        compliance_frameworks=["PCI_DSS_3.2.1"],
        status=FindingStatus.OPEN,
    )
    await db_session.commit()

    res = await client.get("/api/v1/compliance/stats", headers=_auth(token))
    assert res.status_code == 200
    body = res.json()
    assert len(body["frameworks"]) == 2
    assert body["last_updated"] is not None

    fw_by_id = {fw["framework_id"]: fw for fw in body["frameworks"]}

    cis = fw_by_id["CIS_AWS_1.4"]
    assert cis["display_name"] == "CIS AWS Foundations Benchmark v1.4"
    assert cis["total_controls"] == 2
    assert cis["passing"] == 1
    assert cis["failing"] == 1
    assert cis["coverage_pct"] == 50.0

    pci = fw_by_id["PCI_DSS_3.2.1"]
    assert pci["display_name"] == "PCI DSS v3.2.1"
    assert pci["total_controls"] == 1
    assert pci["passing"] == 0
    assert pci["failing"] == 1
    assert pci["coverage_pct"] == 0.0
