"""
AWS Config client — non-compliant finding ingestion via aiobotocore.

Fetches non-compliant Config rule evaluations and yields ConfigFinding objects.
Handles pagination via NextToken for both describe_compliance_by_config_rule
and get_compliance_details_by_config_rule.

Phase 3: real aiobotocore calls.
"""

import logging
from dataclasses import dataclass
from typing import AsyncIterator

import aiobotocore.session
from botocore.exceptions import ClientError

from app.integrations.aws.sts_client import AssumedRoleCredentials

logger = logging.getLogger(__name__)

_MAX_RESULTS_PER_PAGE = 100

_HIGH_RULES = {
    "restricted-ssh",
    "restricted-common-ports",
    "vpc-flow-logs-enabled",
    "root-account-mfa-enabled",
    "iam-root-access-key-check",
    "s3-bucket-public-read-prohibited",
    "s3-bucket-public-write-prohibited",
}


@dataclass
class ConfigFinding:
    """
    Normalized representation of a non-compliant AWS Config rule evaluation.
    Maps to SourceFinding — raw_payload stores the full evaluation result.
    """
    native_id: str          # ConfigRuleEvaluationResultId or ARN
    rule_name: str          # ConfigRule name
    compliance_type: str    # COMPLIANT / NON_COMPLIANT / NOT_APPLICABLE
    severity: str           # mapped from rule_name prefix or MEDIUM default
    resource_id: str        # ResourceId
    resource_type: str      # ResourceType
    region: str
    annotation: str | None  # Annotation field from AWS
    recorded_at: str | None # ResultRecordedTime as ISO string


class ConfigClient:
    """
    Async AWS Config connector.

    Usage:
        client = ConfigClient.from_credentials(assumed_creds, region="us-east-1")
        async for finding in client.iter_noncompliant_findings():
            # finding is a ConfigFinding
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
    ) -> "ConfigClient":
        """Create ConfigClient from AssumedRoleCredentials."""
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

    async def iter_noncompliant_findings(
        self,
        filters: dict | None = None,
    ) -> AsyncIterator[ConfigFinding]:
        """
        Async generator — yields ConfigFinding for each non-compliant resource.

        1. Paginates describe_compliance_by_config_rule with ComplianceTypes=['NON_COMPLIANT']
        2. For each NON_COMPLIANT rule, calls get_compliance_details_by_config_rule
        3. Yields one ConfigFinding per non-compliant resource evaluation
        """
        async with self._session.create_client("config", **self._client_kwargs()) as client:
            # Step 1: get non-compliant rules
            next_token: str | None = None
            page = 0

            while True:
                params: dict = {
                    "ComplianceTypes": ["NON_COMPLIANT"],
                }
                if next_token:
                    params["NextToken"] = next_token

                try:
                    response = await client.describe_compliance_by_config_rule(**params)
                except ClientError as exc:
                    code = exc.response["Error"]["Code"]
                    logger.error(
                        "config.describe_compliance_by_config_rule failed code=%s", code
                    )
                    raise

                rules = response.get("ComplianceByConfigRules", [])
                page += 1
                logger.info(
                    "config.describe_compliance page=%d rules=%d", page, len(rules)
                )

                for rule_entry in rules:
                    compliance = rule_entry.get("Compliance", {})
                    if compliance.get("ComplianceType") != "NON_COMPLIANT":
                        continue

                    rule_name: str = rule_entry.get("ConfigRuleName", "unknown")

                    # Step 2: get evaluation details for this rule
                    async for finding in self._iter_rule_details(
                        client, rule_name
                    ):
                        yield finding

                next_token = response.get("NextToken")
                if not next_token:
                    break

    async def _iter_rule_details(
        self,
        client,
        rule_name: str,
    ) -> AsyncIterator[ConfigFinding]:
        """Paginate get_compliance_details_by_config_rule for a single non-compliant rule."""
        next_token: str | None = None

        while True:
            params: dict = {
                "ConfigRuleName": rule_name,
                "ComplianceTypes": ["NON_COMPLIANT"],
                "Limit": _MAX_RESULTS_PER_PAGE,
            }
            if next_token:
                params["NextToken"] = next_token

            try:
                response = await client.get_compliance_details_by_config_rule(**params)
            except ClientError as exc:
                code = exc.response["Error"]["Code"]
                logger.warning(
                    "config.get_compliance_details failed rule=%s code=%s",
                    rule_name,
                    code,
                )
                return

            results = response.get("EvaluationResults", [])
            for result in results:
                qualifier = result.get("EvaluationResultIdentifier", {})
                resource_key = qualifier.get("EvaluationResultQualifier", {})
                resource_id = resource_key.get("ResourceId", "unknown")
                resource_type = resource_key.get("ResourceType", "unknown")
                compliance_type = result.get("ComplianceType", "NON_COMPLIANT")
                annotation = result.get("Annotation")
                recorded_at_raw = result.get("ResultRecordedTime")
                recorded_at = (
                    recorded_at_raw.isoformat()
                    if hasattr(recorded_at_raw, "isoformat")
                    else str(recorded_at_raw) if recorded_at_raw
                    else None
                )

                # Build a stable native_id from rule + resource
                native_id = f"{rule_name}/{resource_type}/{resource_id}"

                yield ConfigFinding(
                    native_id=native_id,
                    rule_name=rule_name,
                    compliance_type=compliance_type,
                    severity=self._map_severity(rule_name),
                    resource_id=resource_id,
                    resource_type=resource_type,
                    region=self._region,
                    annotation=annotation,
                    recorded_at=recorded_at,
                )

            next_token = response.get("NextToken")
            if not next_token:
                break

    def _map_severity(self, rule_name: str) -> str:
        """Map Config rule name to FindingSeverity value."""
        return "high" if any(h in rule_name.lower() for h in _HIGH_RULES) else "medium"
