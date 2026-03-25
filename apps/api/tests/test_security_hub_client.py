"""
Tests for SecurityHubClient.

Mocks aiobotocore SecurityHub client responses at the aiobotocore client level.
Tests: pagination logic, ASFF mapping, severity mapping, empty accounts.

NOTE: moto is incompatible with aiobotocore 2.15.x (raw_headers missing).
      Severity parametrize tests use pure unit testing — no AWS calls needed.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.integrations.aws.security_hub_client import SecurityHubClient, SecurityHubFinding
from app.integrations.aws.sts_client import AssumedRoleCredentials
from app.models.enums import FindingSeverity


def _fake_creds() -> AssumedRoleCredentials:
    return AssumedRoleCredentials(
        access_key_id="ASIA",
        secret_access_key="sec",
        session_token="tok",
        assumed_role_arn="arn:aws:sts::123456789012:assumed-role/R/s",
        expiration="2099-01-01",
    )


def _asff_finding(finding_id: str, severity: str = "HIGH", resource_arn: str = "arn:aws:s3:::bucket") -> dict:
    return {
        "Id": finding_id,
        "Title": f"Finding {finding_id}",
        "Description": "Test desc",
        "Severity": {"Label": severity},
        "Resources": [{"Type": "AwsS3Bucket", "Id": resource_arn, "Region": "us-east-1"}],
        "Region": "us-east-1",
        "FirstObservedAt": "2024-01-01T00:00:00Z",
        "LastObservedAt": "2024-01-02T00:00:00Z",
        "Types": ["Software and Configuration Checks/Industry and Regulatory Standards/CIS AWS Foundations Benchmark"],
    }


def _mock_hub_client(pages: list[list[dict]], next_tokens: list[str | None] | None = None):
    """Build a mock aiobotocore securityhub client returning the given pages."""
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)

    if next_tokens is None:
        next_tokens = [None] * len(pages)

    responses = []
    for findings, token in zip(pages, next_tokens):
        resp: dict = {"Findings": findings}
        if token:
            resp["NextToken"] = token
        responses.append(resp)

    client.get_findings = AsyncMock(side_effect=responses)
    return client


@pytest.mark.asyncio
async def test_iter_active_findings_single_page():
    """Single page of findings is yielded correctly."""
    findings = [_asff_finding("f-001"), _asff_finding("f-002")]
    mock_client = _mock_hub_client([findings])

    hub = SecurityHubClient(credentials=_fake_creds(), region="us-east-1")
    with patch.object(hub._session, "create_client", return_value=mock_client):
        result = [f async for f in hub.iter_active_findings()]

    assert len(result) == 2
    assert result[0].native_id == "f-001"
    assert result[1].native_id == "f-002"
    assert all(isinstance(f, SecurityHubFinding) for f in result)


@pytest.mark.asyncio
async def test_iter_active_findings_pagination():
    """NextToken pagination yields all findings across pages."""
    page1 = [_asff_finding(f"p1-{i}") for i in range(3)]
    page2 = [_asff_finding(f"p2-{i}") for i in range(2)]
    mock_client = _mock_hub_client([page1, page2], next_tokens=["token-abc", None])

    hub = SecurityHubClient(credentials=_fake_creds(), region="us-east-1")
    with patch.object(hub._session, "create_client", return_value=mock_client):
        result = [f async for f in hub.iter_active_findings()]

    assert len(result) == 5
    # get_findings called twice (2 pages)
    assert mock_client.get_findings.call_count == 2
    # Second call included NextToken
    second_call_kwargs = mock_client.get_findings.call_args_list[1].kwargs
    assert second_call_kwargs.get("NextToken") == "token-abc"


@pytest.mark.asyncio
async def test_iter_active_findings_empty():
    """Empty account yields no findings."""
    mock_client = _mock_hub_client([[]])

    hub = SecurityHubClient(credentials=_fake_creds(), region="us-east-1")
    with patch.object(hub._session, "create_client", return_value=mock_client):
        result = [f async for f in hub.iter_active_findings()]

    assert result == []


@pytest.mark.asyncio
async def test_finding_fields_mapped_correctly():
    """ASFF dict fields map to SecurityHubFinding fields."""
    raw = _asff_finding("map-test-001", severity="CRITICAL", resource_arn="arn:aws:s3:::my-bucket")
    raw["Title"] = "S3 bucket is publicly accessible"
    raw["Description"] = "The bucket allows public read access"
    mock_client = _mock_hub_client([[raw]])

    hub = SecurityHubClient(credentials=_fake_creds(), region="us-east-1")
    with patch.object(hub._session, "create_client", return_value=mock_client):
        result = [f async for f in hub.iter_active_findings()]

    f = result[0]
    assert f.native_id == "map-test-001"
    assert f.title == "S3 bucket is publicly accessible"
    assert f.description == "The bucket allows public read access"
    assert f.severity == FindingSeverity.CRITICAL
    assert f.resource_arn == "arn:aws:s3:::my-bucket"
    assert f.resource_type == "AwsS3Bucket"
    assert f.region == "us-east-1"
    assert f.raw_payload.get("Id") == "map-test-001"


@pytest.mark.parametrize("asff_label,expected", [
    ("CRITICAL", FindingSeverity.CRITICAL),
    ("HIGH", FindingSeverity.HIGH),
    ("MEDIUM", FindingSeverity.MEDIUM),
    ("LOW", FindingSeverity.LOW),
    ("INFORMATIONAL", FindingSeverity.INFO),
    ("UNKNOWN_LABEL", FindingSeverity.INFO),
    ("", FindingSeverity.INFO),
])
def test_map_severity(asff_label: str, expected: FindingSeverity):
    result = SecurityHubClient._map_severity({"Label": asff_label})
    assert result == expected
