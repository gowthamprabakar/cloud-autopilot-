"""
SecurityHubScanner — polls AWS Security Hub get_findings with pagination.

Rules:
- Only fetches ACTIVE, non-ARCHIVED findings.
- Pages up to MAX_PAGES (50 × 100 = 5 000 findings per scan).
- Wraps all boto3 calls with _run_sync to stay async-safe.
"""

import logging
from typing import Any

from app.services.aws_scanner.base_scanner import BaseScanner
from app.services.aws_scanner.normalizer import FindingNormalizer

logger = logging.getLogger(__name__)

MAX_PAGES = 50
PAGE_SIZE = 100


class SecurityHubScanner(BaseScanner):
    """Pulls findings from AWS Security Hub (ASFF format)."""

    def __init__(self, boto3_client: Any, account_id: str, region: str,
                 workspace_id: str, aws_account_uuid: str) -> None:
        super().__init__(boto3_client, account_id, region)
        self.workspace_id = workspace_id
        self.aws_account_uuid = aws_account_uuid
        self.normalizer = FindingNormalizer()

    async def scan(self) -> list[dict]:
        raw_findings = await self._paginate_findings()
        return [
            self.normalizer.from_security_hub(f, self.workspace_id, self.aws_account_uuid)
            for f in raw_findings
        ]

    async def _paginate_findings(self) -> list[dict]:
        findings: list[dict] = []
        filters = {
            "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}],
            "WorkflowStatus": [
                {"Value": "NEW", "Comparison": "EQUALS"},
                {"Value": "NOTIFIED", "Comparison": "EQUALS"},
                {"Value": "IN_PROGRESS", "Comparison": "EQUALS"},
            ],
        }

        def _first_page():
            return self.client.get_findings(
                Filters=filters,
                MaxResults=PAGE_SIZE,
            )

        try:
            response = await self._run_sync(_first_page)
        except Exception as exc:
            # SecurityHub not enabled — treat as empty
            if "not subscribed" in str(exc).lower() or "not enabled" in str(exc).lower():
                logger.info("SecurityHub not enabled for account %s", self.account_id)
                return []
            raise

        findings.extend(response.get("Findings", []))
        next_token = response.get("NextToken")
        pages = 1

        while next_token and pages < MAX_PAGES:
            def _next_page(token=next_token):
                return self.client.get_findings(
                    Filters=filters,
                    MaxResults=PAGE_SIZE,
                    NextToken=token,
                )
            response = await self._run_sync(_next_page)
            findings.extend(response.get("Findings", []))
            next_token = response.get("NextToken")
            pages += 1

        logger.info(
            "SecurityHub: fetched %d findings from account=%s (%d pages)",
            len(findings), self.account_id, pages,
        )
        return findings
