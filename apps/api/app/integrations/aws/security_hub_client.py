"""
AWS Security Hub client — finding ingestion via aiobotocore.

Fetches findings from the Security Hub GetFindings API using assumed-role
credentials. Handles pagination via NextToken.

Default filter: ACTIVE record state + NEW/NOTIFIED workflow status.
This matches findings that need action (excludes archived/suppressed).

Phase 3: real aiobotocore calls wired.
"""

import logging
from dataclasses import dataclass, field
from typing import AsyncIterator

import aiobotocore.session
from botocore.exceptions import ClientError

from app.integrations.aws.sts_client import AssumedRoleCredentials
from app.models.enums import FindingSeverity

logger = logging.getLogger(__name__)

_MAX_RESULTS_PER_PAGE = 100

# Default ASFF filter — active findings not yet suppressed/resolved
_DEFAULT_FILTERS = {
    "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}],
    "WorkflowStatus": [
        {"Value": "NEW", "Comparison": "EQUALS"},
        {"Value": "NOTIFIED", "Comparison": "EQUALS"},
    ],
}


@dataclass
class SecurityHubFinding:
    """
    Normalized representation of a Security Hub ASFF finding.
    Maps to SourceFinding — raw_payload stores the full ASFF dict.
    """
    native_id: str
    title: str
    description: str
    severity: FindingSeverity
    resource_arn: str | None
    resource_type: str | None
    region: str
    first_observed_at: str | None
    last_observed_at: str | None
    raw_payload: dict = field(default_factory=dict)


class SecurityHubClient:
    """
    Async Security Hub connector.

    Usage:
        client = SecurityHubClient(credentials=assumed_creds, region="us-east-1")
        async for finding in client.iter_active_findings():
            # finding is a SecurityHubFinding
            ...
    """

    def __init__(self, credentials: AssumedRoleCredentials, region: str = "us-east-1") -> None:
        self._credentials = credentials
        self._region = region
        self._session = aiobotocore.session.get_session()

    def _client_kwargs(self) -> dict:
        return {
            "region_name": self._region,
            "aws_access_key_id": self._credentials.access_key_id,
            "aws_secret_access_key": self._credentials.secret_access_key,
            "aws_session_token": self._credentials.session_token,
        }

    async def iter_active_findings(
        self,
        filters: dict | None = None,
    ) -> AsyncIterator[SecurityHubFinding]:
        """
        Async generator — paginates GetFindings and yields SecurityHubFinding.

        Fetches up to _MAX_RESULTS_PER_PAGE per API call and follows NextToken
        until all findings are exhausted.
        """
        active_filters = filters or _DEFAULT_FILTERS
        next_token: str | None = None
        page = 0

        logger.info("security_hub.iter_active_findings region=%s", self._region)

        async with self._session.create_client("securityhub", **self._client_kwargs()) as client:
            while True:
                params: dict = {
                    "Filters": active_filters,
                    "MaxResults": _MAX_RESULTS_PER_PAGE,
                }
                if next_token:
                    params["NextToken"] = next_token

                try:
                    response = await client.get_findings(**params)
                except ClientError as exc:
                    code = exc.response["Error"]["Code"]
                    logger.error("security_hub.get_findings failed code=%s", code)
                    raise

                findings = response.get("Findings", [])
                page += 1
                logger.info("security_hub.page page=%d findings=%d", page, len(findings))

                for raw in findings:
                    yield self._map_finding(raw)

                next_token = response.get("NextToken")
                if not next_token:
                    break

    def _map_finding(self, raw: dict) -> SecurityHubFinding:
        """Map raw ASFF dict → SecurityHubFinding."""
        resources = raw.get("Resources", [])
        first_resource = resources[0] if resources else {}

        return SecurityHubFinding(
            native_id=raw["Id"],
            title=raw.get("Title", ""),
            description=raw.get("Description", ""),
            severity=self._map_severity(raw.get("Severity", {})),
            resource_arn=first_resource.get("Id"),
            resource_type=first_resource.get("Type"),
            region=raw.get("Region", self._region),
            first_observed_at=raw.get("FirstObservedAt"),
            last_observed_at=raw.get("LastObservedAt"),
            raw_payload=raw,
        )

    @staticmethod
    def _map_severity(asff_severity: dict) -> FindingSeverity:
        """
        Map ASFF severity label to FindingSeverity enum.
        ASFF labels: CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL
        """
        label = (asff_severity.get("Label") or "").upper()
        mapping = {
            "CRITICAL": FindingSeverity.CRITICAL,
            "HIGH": FindingSeverity.HIGH,
            "MEDIUM": FindingSeverity.MEDIUM,
            "LOW": FindingSeverity.LOW,
            "INFORMATIONAL": FindingSeverity.INFO,
        }
        return mapping.get(label, FindingSeverity.INFO)
