"""
ConfigScanner — fetches non-compliant AWS Config rule evaluations.

Rules:
- Lists all Config rules, then fetches NON_COMPLIANT evaluations per rule.
- Handles case where Config is not enabled (returns []).
- Each non-compliant resource becomes one canonical finding.
"""

import logging
from typing import Any

from app.services.aws_scanner.base_scanner import BaseScanner
from app.services.aws_scanner.normalizer import FindingNormalizer

logger = logging.getLogger(__name__)


class ConfigScanner(BaseScanner):
    """Pulls non-compliant findings from AWS Config."""

    def __init__(self, boto3_client: Any, account_id: str, region: str,
                 workspace_id: str, aws_account_uuid: str) -> None:
        super().__init__(boto3_client, account_id, region)
        self.workspace_id = workspace_id
        self.aws_account_uuid = aws_account_uuid
        self.normalizer = FindingNormalizer()

    async def scan(self) -> list[dict]:
        rule_names = await self._list_rule_names()
        if not rule_names:
            return []

        all_evaluations: list[dict] = []
        for rule_name in rule_names:
            evaluations = await self._get_non_compliant(rule_name)
            all_evaluations.extend(evaluations)

        return [
            self.normalizer.from_config(e, self.workspace_id, self.aws_account_uuid)
            for e in all_evaluations
        ]

    async def _list_rule_names(self) -> list[str]:
        rule_names: list[str] = []

        def _describe(next_token=None):
            kwargs: dict = {}
            if next_token:
                kwargs["NextToken"] = next_token
            return self.client.describe_config_rules(**kwargs)

        try:
            response = await self._run_sync(_describe)
        except Exception as exc:
            exc_str = str(exc).lower()
            if any(k in exc_str for k in ("not enabled", "not set up", "no delivery channel")):
                logger.info("AWS Config not enabled for account=%s", self.account_id)
                return []
            raise

        for rule in response.get("ConfigRules", []):
            rule_names.append(rule["ConfigRuleName"])

        next_token = response.get("NextToken")
        while next_token:
            response = await self._run_sync(lambda t=next_token: _describe(t))
            for rule in response.get("ConfigRules", []):
                rule_names.append(rule["ConfigRuleName"])
            next_token = response.get("NextToken")

        logger.debug("Config: found %d rules for account=%s", len(rule_names), self.account_id)
        return rule_names

    async def _get_non_compliant(self, rule_name: str) -> list[dict]:
        """Fetch NON_COMPLIANT evaluations for a single Config rule."""
        evaluations: list[dict] = []

        def _get(next_token=None):
            kwargs: dict = {
                "ConfigRuleName": rule_name,
                "ComplianceTypes": ["NON_COMPLIANT"],
            }
            if next_token:
                kwargs["NextToken"] = next_token
            return self.client.get_compliance_details_by_config_rule(**kwargs)

        try:
            response = await self._run_sync(_get)
        except Exception:
            # Rule may not have evaluations yet — skip silently
            return []

        for item in response.get("EvaluationResults", []):
            qualifier = item.get("EvaluationResultIdentifier", {}).get(
                "EvaluationResultQualifier", {}
            )
            evaluations.append({
                "ConfigRuleName": rule_name,
                "ResourceId": qualifier.get("ResourceId", ""),
                "ResourceType": qualifier.get("ResourceType", ""),
                "Annotation": item.get("Annotation", ""),
                "OrderingTimestamp": item.get("ResultRecordedTime"),
            })

        next_token = response.get("NextToken")
        while next_token:
            response = await self._run_sync(lambda t=next_token: _get(t))
            for item in response.get("EvaluationResults", []):
                qualifier = item.get("EvaluationResultIdentifier", {}).get(
                    "EvaluationResultQualifier", {}
                )
                evaluations.append({
                    "ConfigRuleName": rule_name,
                    "ResourceId": qualifier.get("ResourceId", ""),
                    "ResourceType": qualifier.get("ResourceType", ""),
                    "Annotation": item.get("Annotation", ""),
                    "OrderingTimestamp": item.get("ResultRecordedTime"),
                })
            next_token = response.get("NextToken")

        return evaluations
