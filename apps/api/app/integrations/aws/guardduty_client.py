"""
AWS GuardDuty client — active finding ingestion via aiobotocore.

Fetches active GuardDuty findings and yields GuardDutyFinding objects.
Handles pagination via NextToken for list_findings and batches of 50
for get_findings.

Phase 3: real aiobotocore calls.
"""

import logging
from dataclasses import dataclass, field
from typing import AsyncIterator

import aiobotocore.session
from botocore.exceptions import ClientError

from app.integrations.aws.sts_client import AssumedRoleCredentials

logger = logging.getLogger(__name__)

_GET_FINDINGS_BATCH_SIZE = 50
_LIST_FINDINGS_MAX_RESULTS = 50

# GuardDuty severity is a float 1.0–10.0
# Mapping: 7-10 → critical, 5-7 → high, 3-5 → medium, 1-3 → low, else → info
def _map_severity(numeric: float) -> str:
    if numeric >= 7.0:
        return "critical"
    if numeric >= 5.0:
        return "high"
    if numeric >= 3.0:
        return "medium"
    if numeric >= 1.0:
        return "low"
    return "info"


@dataclass
class GuardDutyFinding:
    """
    Normalized representation of a GuardDuty finding.
    Maps to SourceFinding — raw_payload stores the full GuardDuty dict.
    """
    native_id: str          # Finding Id
    title: str
    description: str | None
    severity: str           # mapped from GuardDuty 0-10 scale → our enum
    resource_arn: str | None
    resource_type: str | None  # e.g. "AwsEc2Instance"
    region: str
    first_seen_at: str | None
    last_seen_at: str | None
    raw_payload: dict = field(default_factory=dict)


class GuardDutyClient:
    """
    Async GuardDuty connector.

    Usage:
        client = GuardDutyClient.from_credentials(assumed_creds, region="us-east-1")
        detectors = await client.list_detectors()
        async for finding in client.iter_active_findings(detectors[0]):
            # finding is a GuardDutyFinding
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
    ) -> "GuardDutyClient":
        """Create GuardDutyClient from AssumedRoleCredentials."""
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

    async def list_detectors(self) -> list[str]:
        """Returns list of detector IDs in this account/region."""
        detector_ids: list[str] = []
        next_token: str | None = None

        async with self._session.create_client("guardduty", **self._client_kwargs()) as client:
            while True:
                params: dict = {"MaxResults": 50}
                if next_token:
                    params["NextToken"] = next_token

                try:
                    response = await client.list_detectors(**params)
                except ClientError as exc:
                    code = exc.response["Error"]["Code"]
                    logger.error("guardduty.list_detectors failed code=%s", code)
                    raise

                detector_ids.extend(response.get("DetectorIds", []))
                next_token = response.get("NextToken")
                if not next_token:
                    break

        logger.info("guardduty.list_detectors count=%d region=%s", len(detector_ids), self._region)
        return detector_ids

    async def iter_active_findings(
        self, detector_id: str
    ) -> AsyncIterator[GuardDutyFinding]:
        """
        Async generator — yields GuardDutyFinding for each active finding.

        1. list_findings with ACTIVE criterion, paginated via NextToken
        2. get_findings in batches of 50 to retrieve full finding details
        """
        async with self._session.create_client("guardduty", **self._client_kwargs()) as client:
            next_token: str | None = None
            page = 0

            while True:
                params: dict = {
                    "DetectorId": detector_id,
                    "FindingCriteria": {
                        "Criterion": {
                            "service.archived": {
                                "Eq": ["false"],
                            }
                        }
                    },
                    "MaxResults": _LIST_FINDINGS_MAX_RESULTS,
                }
                if next_token:
                    params["NextToken"] = next_token

                try:
                    list_response = await client.list_findings(**params)
                except ClientError as exc:
                    code = exc.response["Error"]["Code"]
                    logger.error(
                        "guardduty.list_findings failed detector=%s code=%s",
                        detector_id,
                        code,
                    )
                    raise

                finding_ids = list_response.get("FindingIds", [])
                page += 1
                logger.info(
                    "guardduty.list_findings page=%d finding_ids=%d",
                    page,
                    len(finding_ids),
                )

                # Fetch details in batches of 50
                for i in range(0, len(finding_ids), _GET_FINDINGS_BATCH_SIZE):
                    batch_ids = finding_ids[i: i + _GET_FINDINGS_BATCH_SIZE]
                    try:
                        get_response = await client.get_findings(
                            DetectorId=detector_id,
                            FindingIds=batch_ids,
                        )
                    except ClientError as exc:
                        code = exc.response["Error"]["Code"]
                        logger.error(
                            "guardduty.get_findings failed detector=%s code=%s",
                            detector_id,
                            code,
                        )
                        raise

                    for raw in get_response.get("Findings", []):
                        yield self._map_finding(raw)

                next_token = list_response.get("NextToken")
                if not next_token:
                    break

    def _map_finding(self, raw: dict) -> GuardDutyFinding:
        """Map raw GuardDuty finding dict → GuardDutyFinding."""
        resource_raw = raw.get("Resource", {})
        resource_type = resource_raw.get("ResourceType")

        # Try to build a resource ARN from available fields
        instance_details = resource_raw.get("InstanceDetails", {})
        resource_arn = instance_details.get("IamInstanceProfile", {}).get("Arn")

        service = raw.get("Service", {})
        first_seen_raw = service.get("EventFirstSeen")
        last_seen_raw = service.get("EventLastSeen")

        first_seen_at = (
            first_seen_raw.isoformat()
            if hasattr(first_seen_raw, "isoformat")
            else str(first_seen_raw) if first_seen_raw
            else None
        )
        last_seen_at = (
            last_seen_raw.isoformat()
            if hasattr(last_seen_raw, "isoformat")
            else str(last_seen_raw) if last_seen_raw
            else None
        )

        numeric_severity = float(raw.get("Severity", 0.0))

        return GuardDutyFinding(
            native_id=raw["Id"],
            title=raw.get("Title", ""),
            description=raw.get("Description"),
            severity=_map_severity(numeric_severity),
            resource_arn=resource_arn,
            resource_type=resource_type,
            region=raw.get("Region", self._region),
            first_seen_at=first_seen_at,
            last_seen_at=last_seen_at,
            raw_payload=raw,
        )
