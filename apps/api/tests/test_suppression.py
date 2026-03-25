"""
Suppression rules API tests — Sprint 9.

Strategy:
- HTTP-level tests with SQLite in-memory DB.
- Canonical findings are inserted directly via db_session fixture.
- Admin user is the first registered user (super_admin role by default).
- Analyst user is invited by admin, then logged in.
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
    "tenant_name": "Suppression Corp",
    "tenant_slug": "suppression-corp",
    "workspace_name": "Production",
    "email": "admin@suppression.example.com",
    "password": "securepw123!",
    "full_name": "Suppression Admin",
    "plan": "baseline",
}


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _get_admin_token(client: AsyncClient, payload: dict | None = None) -> str:
    p = payload or REGISTER_PAYLOAD
    res = await client.post("/api/v1/auth/register", json=p)
    assert res.status_code == 201, res.text
    return res.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _login(client: AsyncClient, email: str, password: str) -> str:
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


async def _get_analyst_token(client: AsyncClient, admin_token: str) -> str:
    """Invite an analyst and return their token."""
    invite_res = await client.post(
        "/api/v1/users/invite",
        json={
            "email": "analyst@suppression.example.com",
            "full_name": "Analyst User",
            "role": "analyst",
            "password": "analystpw123!",
        },
        headers=_auth(admin_token),
    )
    assert invite_res.status_code == 201, invite_res.text
    return await _login(client, "analyst@suppression.example.com", "analystpw123!")


async def _seed_finding(
    db,
    workspace_id: uuid.UUID,
    aws_account_id: uuid.UUID,
    *,
    title: str = "Test Finding",
    severity: FindingSeverity = FindingSeverity.HIGH,
    status: FindingStatus = FindingStatus.OPEN,
    resource_type: str = "AwsS3Bucket",
    resource_arn: str = "arn:aws:s3:::test-bucket",
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
        risk_score=7.5,
        title=title,
        description="Test description",
        remediation="Fix it",
        resource_arn=resource_arn,
        resource_type=resource_type,
        region="us-east-1",
        compliance_frameworks=[],
        tags={},
        first_seen_at="2024-01-01T00:00:00Z",
        last_seen_at="2024-01-02T00:00:00Z",
    )
    db.add(finding)
    await db.flush()
    await db.refresh(finding)
    return finding


async def _seed_aws_account(db, workspace_id: uuid.UUID, account_id: str = "111122223333") -> AwsAccount:
    acct = AwsAccount(
        workspace_id=workspace_id,
        account_id=account_id,
        role_arn=f"arn:aws:iam::{account_id}:role/TestRole",
        status=AwsAccountStatus.ACTIVE,
    )
    db.add(acct)
    await db.flush()
    return acct


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_suppression_rules_empty(client: AsyncClient):
    """GET /suppression-rules returns empty list when no rules exist."""
    token = await _get_admin_token(client)
    res = await client.get("/api/v1/suppression-rules", headers=_auth(token))
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.asyncio
async def test_create_suppression_rule(client: AsyncClient):
    """POST /suppression-rules creates a rule and returns 201."""
    token = await _get_admin_token(client)
    payload = {
        "name": "Suppress low S3 findings",
        "reason": "Accepted risk for this resource type",
        "match_title_contains": "S3",
        "match_severity": "low",
    }
    res = await client.post("/api/v1/suppression-rules", json=payload, headers=_auth(token))
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["name"] == "Suppress low S3 findings"
    assert body["reason"] == "Accepted risk for this resource type"
    assert body["match_title_contains"] == "S3"
    assert body["match_severity"] == "low"
    assert body["is_active"] is True
    assert "id" in body

    # Verify rule shows in list
    list_res = await client.get("/api/v1/suppression-rules", headers=_auth(token))
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1


@pytest.mark.asyncio
async def test_create_rule_requires_admin(client: AsyncClient):
    """Analyst cannot create a suppression rule — expects 403."""
    admin_token = await _get_admin_token(client)
    analyst_token = await _get_analyst_token(client, admin_token)

    payload = {
        "name": "Analyst rule",
        "reason": "Should not be allowed",
    }
    res = await client.post(
        "/api/v1/suppression-rules", json=payload, headers=_auth(analyst_token)
    )
    assert res.status_code == 403, res.text


@pytest.mark.asyncio
async def test_delete_suppression_rule(client: AsyncClient):
    """DELETE /suppression-rules/{id} soft-deletes the rule; it no longer appears in list."""
    token = await _get_admin_token(client)

    # Create a rule
    create_res = await client.post(
        "/api/v1/suppression-rules",
        json={"name": "To Delete", "reason": "Test"},
        headers=_auth(token),
    )
    assert create_res.status_code == 201
    rule_id = create_res.json()["id"]

    # Delete it
    del_res = await client.delete(
        f"/api/v1/suppression-rules/{rule_id}", headers=_auth(token)
    )
    assert del_res.status_code == 204

    # It is soft-deleted — is_active=False, but the rule still exists in the DB
    # The list endpoint returns all rules (active and inactive)
    list_res = await client.get("/api/v1/suppression-rules", headers=_auth(token))
    assert list_res.status_code == 200
    rules = list_res.json()
    # The rule is in the list but is_active is False
    matching = [r for r in rules if r["id"] == rule_id]
    assert len(matching) == 1
    assert matching[0]["is_active"] is False


@pytest.mark.asyncio
async def test_delete_rule_requires_admin(client: AsyncClient):
    """Analyst cannot delete a suppression rule — expects 403."""
    admin_token = await _get_admin_token(client)
    analyst_token = await _get_analyst_token(client, admin_token)

    # Admin creates a rule
    create_res = await client.post(
        "/api/v1/suppression-rules",
        json={"name": "Admin Rule", "reason": "For test"},
        headers=_auth(admin_token),
    )
    assert create_res.status_code == 201
    rule_id = create_res.json()["id"]

    # Analyst tries to delete — should 403
    del_res = await client.delete(
        f"/api/v1/suppression-rules/{rule_id}", headers=_auth(analyst_token)
    )
    assert del_res.status_code == 403


@pytest.mark.asyncio
async def test_suppression_rule_workspace_isolation(client: AsyncClient):
    """User A cannot see User B's suppression rules."""
    # Register user A
    token_a = await _get_admin_token(
        client,
        {
            "tenant_name": "Company A",
            "tenant_slug": "company-a-supp",
            "workspace_name": "Workspace A",
            "email": "admin@company-a-supp.example.com",
            "password": "passwordA123!",
            "full_name": "Admin A",
            "plan": "baseline",
        },
    )

    # Register user B
    token_b = await _get_admin_token(
        client,
        {
            "tenant_name": "Company B",
            "tenant_slug": "company-b-supp",
            "workspace_name": "Workspace B",
            "email": "admin@company-b-supp.example.com",
            "password": "passwordB123!",
            "full_name": "Admin B",
            "plan": "baseline",
        },
    )

    # B creates a rule
    create_res = await client.post(
        "/api/v1/suppression-rules",
        json={"name": "B's Rule", "reason": "B's reason"},
        headers=_auth(token_b),
    )
    assert create_res.status_code == 201

    # A lists rules — should be empty
    list_res = await client.get("/api/v1/suppression-rules", headers=_auth(token_a))
    assert list_res.status_code == 200
    assert list_res.json() == []


@pytest.mark.asyncio
async def test_apply_rules_suppresses_matching_findings(
    client: AsyncClient, db_session
):
    """Create a rule matching by title; apply; matching OPEN finding becomes SUPPRESSED."""
    token = await _get_admin_token(client)
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    workspace_id = uuid.UUID(me_res.json()["workspace_id"])

    acct = await _seed_aws_account(db_session, workspace_id, "100200300400")
    finding = await _seed_finding(
        db_session,
        workspace_id,
        acct.id,
        title="S3 Bucket Public Access",
        status=FindingStatus.OPEN,
    )
    await db_session.commit()

    # Create a matching suppression rule
    create_res = await client.post(
        "/api/v1/suppression-rules",
        json={
            "name": "Suppress S3 findings",
            "reason": "Accepted risk",
            "match_title_contains": "S3 Bucket",
        },
        headers=_auth(token),
    )
    assert create_res.status_code == 201

    # Apply rules
    apply_res = await client.post("/api/v1/suppression-rules/apply", headers=_auth(token))
    assert apply_res.status_code == 200
    body = apply_res.json()
    assert body["suppressed"] == 1

    # Verify finding is now SUPPRESSED
    finding_res = await client.get(
        f"/api/v1/findings/{finding.id}", headers=_auth(token)
    )
    assert finding_res.status_code == 200
    assert finding_res.json()["status"] == "suppressed"


@pytest.mark.asyncio
async def test_apply_rules_no_match(client: AsyncClient, db_session):
    """Rule with non-matching title — finding stays OPEN."""
    token = await _get_admin_token(client)
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    workspace_id = uuid.UUID(me_res.json()["workspace_id"])

    acct = await _seed_aws_account(db_session, workspace_id, "200300400500")
    finding = await _seed_finding(
        db_session,
        workspace_id,
        acct.id,
        title="IAM User has no MFA",
        status=FindingStatus.OPEN,
    )
    await db_session.commit()

    # Create a rule that does NOT match
    create_res = await client.post(
        "/api/v1/suppression-rules",
        json={
            "name": "Suppress EC2 findings",
            "reason": "Accepted risk",
            "match_title_contains": "EC2 Instance",
        },
        headers=_auth(token),
    )
    assert create_res.status_code == 201

    apply_res = await client.post("/api/v1/suppression-rules/apply", headers=_auth(token))
    assert apply_res.status_code == 200
    assert apply_res.json()["suppressed"] == 0

    # Finding is still OPEN
    finding_res = await client.get(
        f"/api/v1/findings/{finding.id}", headers=_auth(token)
    )
    assert finding_res.status_code == 200
    assert finding_res.json()["status"] == "open"


@pytest.mark.asyncio
async def test_suppression_rule_invalid_severity(client: AsyncClient):
    """POST with invalid match_severity returns 422."""
    token = await _get_admin_token(client)
    res = await client.post(
        "/api/v1/suppression-rules",
        json={
            "name": "Bad Severity",
            "reason": "test",
            "match_severity": "not_a_valid_severity",
        },
        headers=_auth(token),
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_suppression_requires_auth(client: AsyncClient):
    """GET /suppression-rules without token returns 401."""
    res = await client.get("/api/v1/suppression-rules")
    assert res.status_code == 401
