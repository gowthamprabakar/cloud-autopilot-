"""
AWS Inspector v2 client — vulnerability finding ingestion via aiobotocore.

Uses the inspector2 service (modern Inspector, not classic inspector).
Fetches active findings: container image vulnerabilities, EC2 package
vulnerabilities, and network reachability findings.

Phase 3: real aiobotocore calls.
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

_SEVERITY_MAP = {
    "CRITICAL": FindingSeverity.CRITICAL,
    "HIGH": FindingSeverity.HIGH,
    "MEDIUM": FindingSeverity.MEDIUM,
    "LOW": FindingSeverity.LOW,
    "INFORMATIONAL": FindingSeverity.INFO,
    "UNTRIAGED": FindingSeverity.INFO,
}


@dataclass
class InspectorFinding:
    """
    Normalized representation of an AWS Inspector v2 finding.
    Maps to SourceFinding — raw_payload stores the full Inspector dict.
    """
    native_id: str           # findingArn
    title: str
    description: str | None
    severity: FindingSeverity
    resource_arn: str | None  # resources[0].id
    resource_type: str | None # resources[0].type (e.g. AWS_ECR_CONTAINER_IMAGE)
    region: str
    finding_type: str | None  # PACKAGE_VULNERABILITY, NETWORK_REACHABILITY, etc.
    first_observed_at: str | None
    last_observed_at: str | None
    raw_payload: dict = field(default_factory=dict)


class InspectorClient:
    """
    Async Inspector v2 connector.

    Usage:
        client = InspectorClient.from_credentials(assumed_creds, region="us-east-1")
        async for finding in client.iter_active_findings():
            # finding is an InspectorFinding
            ...
    """

    def __init__(
        self,
        access_key_id: str,
        secret_access_key: str,
        session_token: str,
        region: str = "us-east-1",
    ) -> None:
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._session_token = session_token
        self._region = region
        self._session = aiobotocore.session.get_session()

    @classmethod
    def from_credentials(
        cls,
        credentials: AssumedRoleCredentials,
        region: str = "us-east-1",
    ) -> "InspectorClient":
        return cls(
            access_key_id=credentials.access_key_id,
            secret_access_key=credentials.secret_access_key,
            session_token=credentials.session_token,
            region=region,
        )

    def _client_kwargs(self) -> dict:
        return {
            "region_name": self._region,
            "aws_access_key_id": self._access_key_id,
            "aws_secret_access_key": self._secret_access_key,
            "aws_session_token": self._session_token,
        }

    async def iter_active_findings(self) -> AsyncIterator[InspectorFinding]:
        """
        Async generator — paginates list_findings with ACTIVE filter.
        Yields InspectorFinding for each active finding.
        """
        next_token: str | None = None
        page = 0

        logger.info("inspector.iter_active_findings region=%s", self._region)

        async with self._session.create_client("inspector2", **self._client_kwargs()) as client:
            while True:
                params: dict = {
                    "filterCriteria": {
                        "findingStatus": [
                            {"comparison": "EQUALS", "value": "ACTIVE"}
                        ]
                    },
                    "maxResults": _MAX_RESULTS_PER_PAGE,
                }
                if next_token:
                    params["nextToken"] = next_token

                try:
                    response = await client.list_findings(**params)
                except ClientError as exc:
                    code = exc.response["Error"]["Code"]
                    # Inspector may not be enabled — treat as empty, log warning
                    if code in ("AccessDeniedException", "ValidationException"):
                        logger.warning(
                            "inspector.list_findings skipped code=%s region=%s",
                            code,
                            self._region,
                        )
                        return
                    logger.error("inspector.list_findings failed code=%s", code)
                    raise

                findings = response.get("findings", [])
                page += 1
                logger.info(
                    "inspector.page page=%d findings=%d region=%s",
                    page,
                    len(findings),
                    self._region,
                )

                for raw in findings:
                    yield self._map_finding(raw)

                next_token = response.get("nextToken")
                if not next_token:
                    break

    def _map_finding(self, raw: dict) -> InspectorFinding:
        """Map raw Inspector v2 finding dict → InspectorFinding."""
        resources = raw.get("resources", [])
        first_resource = resources[0] if resources else {}

        first_obs = raw.get("firstObservedAt")
        last_obs = raw.get("lastObservedAt")

        first_observed_at = (
            first_obs.isoformat()
            if hasattr(first_obs, "isoformat")
            else str(first_obs) if first_obs else None
        )
        last_observed_at = (
            last_obs.isoformat()
            if hasattr(last_obs, "isoformat")
            else str(last_obs) if last_obs else None
        )

        severity_label = (
            raw.get("severity", {}).get("label", "INFORMATIONAL").upper()
        )

        return InspectorFinding(
            native_id=raw["findingArn"],
            title=raw.get("title", ""),
            description=raw.get("description"),
            severity=_SEVERITY_MAP.get(severity_label, FindingSeverity.INFO),
            resource_arn=first_resource.get("id"),
            resource_type=first_resource.get("type"),
            region=first_resource.get("region", self._region),
            finding_type=raw.get("type"),
            first_observed_at=first_observed_at,
            last_observed_at=last_observed_at,
            raw_payload=raw,
        )
