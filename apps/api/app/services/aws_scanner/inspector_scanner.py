"""
InspectorScanner — polls AWS Inspector v2 list_findings.

Rules:
- Gracefully handles AccessDeniedException (LocalStack free tier / not enabled).
- Only fetches ACTIVE findings.
- Pagination via nextToken.
"""

import logging
from typing import Any

from app.services.aws_scanner.base_scanner import BaseScanner
from app.services.aws_scanner.normalizer import FindingNormalizer

logger = logging.getLogger(__name__)

PAGE_SIZE = 100
MAX_PAGES = 50


class InspectorScanner(BaseScanner):
    """Pulls findings from AWS Inspector v2."""

    def __init__(self, boto3_client: Any, account_id: str, region: str,
                 workspace_id: str, aws_account_uuid: str) -> None:
        super().__init__(boto3_client, account_id, region)
        self.workspace_id = workspace_id
        self.aws_account_uuid = aws_account_uuid
        self.normalizer = FindingNormalizer()

    async def scan(self) -> list[dict]:
        raw_findings = await self._paginate_findings()
        return [
            self.normalizer.from_inspector(f, self.workspace_id, self.aws_account_uuid)
            for f in raw_findings
        ]

    async def _paginate_findings(self) -> list[dict]:
        findings: list[dict] = []
        filter_criteria = {
            "findingStatus": [{"comparison": "EQUALS", "value": "ACTIVE"}]
        }

        def _first():
            return self.client.list_findings(
                filterCriteria=filter_criteria,
                maxResults=PAGE_SIZE,
            )

        try:
            response = await self._run_sync(_first)
        except Exception as exc:
            exc_name = type(exc).__name__
            exc_str = str(exc).lower()
            if any(k in exc_name for k in ("AccessDenied", "ValidationException")) or \
               any(k in exc_str for k in ("not enabled", "not activated", "not subscribed")):
                logger.info(
                    "Inspector v2 not available for account=%s (free tier / not enabled): %s",
                    self.account_id, exc,
                )
                return []
            raise

        findings.extend(response.get("findings", []))
        next_token = response.get("nextToken")
        pages = 1

        while next_token and pages < MAX_PAGES:
            def _next(token=next_token):
                return self.client.list_findings(
                    filterCriteria=filter_criteria,
                    maxResults=PAGE_SIZE,
                    nextToken=token,
                )
            response = await self._run_sync(_next)
            findings.extend(response.get("findings", []))
            next_token = response.get("nextToken")
            pages += 1

        logger.info(
            "Inspector: fetched %d findings from account=%s (%d pages)",
            len(findings), self.account_id, pages,
        )
        return findings
