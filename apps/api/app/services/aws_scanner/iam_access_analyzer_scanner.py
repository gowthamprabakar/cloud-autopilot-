"""
IAMAccessAnalyzerScanner — lists analyzers and fetches their findings.

Rules:
- Lists all analyzers in the region, fetches ACTIVE findings for each.
- Gracefully handles case where Access Analyzer is not enabled.
- Maps ExternalAccess and UnusedAccess finding types.
"""

import logging
from typing import Any

from app.services.aws_scanner.base_scanner import BaseScanner
from app.services.aws_scanner.normalizer import FindingNormalizer

logger = logging.getLogger(__name__)


class IAMAccessAnalyzerScanner(BaseScanner):
    """Pulls findings from AWS IAM Access Analyzer."""

    def __init__(self, boto3_client: Any, account_id: str, region: str,
                 workspace_id: str, aws_account_uuid: str) -> None:
        super().__init__(boto3_client, account_id, region)
        self.workspace_id = workspace_id
        self.aws_account_uuid = aws_account_uuid
        self.normalizer = FindingNormalizer()

    async def scan(self) -> list[dict]:
        analyzer_arns = await self._list_analyzers()
        if not analyzer_arns:
            return []

        all_findings: list[dict] = []
        for arn in analyzer_arns:
            findings = await self._list_findings(arn)
            all_findings.extend(findings)

        return [
            self.normalizer.from_iam_access_analyzer(f, self.workspace_id, self.aws_account_uuid)
            for f in all_findings
        ]

    async def _list_analyzers(self) -> list[str]:
        try:
            response = await self._run_sync(self.client.list_analyzers)
            analyzers = response.get("analyzers", [])
            arns = [a["arn"] for a in analyzers if a.get("status") == "ACTIVE"]
            if not arns:
                logger.info(
                    "IAM Access Analyzer: no active analyzers for account=%s region=%s",
                    self.account_id, self.region,
                )
            return arns
        except Exception as exc:
            exc_str = str(exc).lower()
            if any(k in exc_str for k in ("not enabled", "access denied", "not authorized")):
                logger.info(
                    "IAM Access Analyzer not enabled for account=%s: %s",
                    self.account_id, exc,
                )
                return []
            raise

    async def _list_findings(self, analyzer_arn: str) -> list[dict]:
        findings: list[dict] = []

        def _list(next_token=None):
            kwargs: dict = {
                "analyzerArn": analyzer_arn,
                "filter": {"status": {"eq": ["ACTIVE"]}},
                "maxResults": 100,
            }
            if next_token:
                kwargs["nextToken"] = next_token
            return self.client.list_findings_v2(**kwargs)

        try:
            response = await self._run_sync(_list)
        except Exception:
            # Try v1 API as fallback
            try:
                def _list_v1(next_token=None):
                    kwargs: dict = {
                        "analyzerArn": analyzer_arn,
                        "filter": {"status": {"eq": ["ACTIVE"]}},
                        "maxResults": 100,
                    }
                    if next_token:
                        kwargs["nextToken"] = next_token
                    return self.client.list_findings(**kwargs)
                response = await self._run_sync(_list_v1)
            except Exception as exc2:
                logger.warning("IAM Access Analyzer list_findings failed: %s", exc2)
                return []

        findings.extend(response.get("findings", []))
        next_token = response.get("nextToken")

        while next_token:
            response = await self._run_sync(lambda t=next_token: _list(t))
            findings.extend(response.get("findings", []))
            next_token = response.get("nextToken")

        logger.info(
            "IAM Access Analyzer: %d findings from %s", len(findings), analyzer_arn
        )
        return findings
