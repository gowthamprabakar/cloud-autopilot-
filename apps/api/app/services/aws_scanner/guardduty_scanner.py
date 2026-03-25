"""
GuardDutyScanner — lists detectors, then fetches active findings.

Rules:
- Handles case where GuardDuty is not enabled (returns []).
- get_findings batch size capped at 50 (AWS API limit).
- Only fetches non-archived findings.
"""

import logging
from typing import Any

from app.services.aws_scanner.base_scanner import BaseScanner
from app.services.aws_scanner.normalizer import FindingNormalizer

logger = logging.getLogger(__name__)

BATCH_SIZE = 50  # AWS hard limit for get_findings


class GuardDutyScanner(BaseScanner):
    """Pulls findings from AWS GuardDuty."""

    def __init__(self, boto3_client: Any, account_id: str, region: str,
                 workspace_id: str, aws_account_uuid: str) -> None:
        super().__init__(boto3_client, account_id, region)
        self.workspace_id = workspace_id
        self.aws_account_uuid = aws_account_uuid
        self.normalizer = FindingNormalizer()

    async def scan(self) -> list[dict]:
        detector_id = await self._get_detector_id()
        if not detector_id:
            return []

        finding_ids = await self._list_finding_ids(detector_id)
        if not finding_ids:
            return []

        raw_findings = await self._get_findings_batch(detector_id, finding_ids)
        return [
            self.normalizer.from_guard_duty(f, self.workspace_id, self.aws_account_uuid)
            for f in raw_findings
        ]

    async def _get_detector_id(self) -> str | None:
        try:
            response = await self._run_sync(self.client.list_detectors)
            detector_ids = response.get("DetectorIds", [])
            if not detector_ids:
                logger.info("GuardDuty: no detectors found for account=%s", self.account_id)
                return None
            return detector_ids[0]
        except Exception as exc:
            if "not enabled" in str(exc).lower() or "BadRequestException" in str(type(exc).__name__):
                logger.info("GuardDuty not enabled for account=%s", self.account_id)
                return None
            raise

    async def _list_finding_ids(self, detector_id: str) -> list[str]:
        finding_ids: list[str] = []

        def _list(next_token=None):
            kwargs: dict = {
                "DetectorId": detector_id,
                "FindingCriteria": {
                    "Criterion": {
                        "service.archived": {"Eq": ["false"]}
                    }
                },
                "MaxResults": 50,
            }
            if next_token:
                kwargs["NextToken"] = next_token
            return self.client.list_findings(**kwargs)

        response = await self._run_sync(_list)
        finding_ids.extend(response.get("FindingIds", []))
        next_token = response.get("NextToken")

        while next_token:
            response = await self._run_sync(lambda t=next_token: _list(t))
            finding_ids.extend(response.get("FindingIds", []))
            next_token = response.get("NextToken")

        return finding_ids

    async def _get_findings_batch(self, detector_id: str, finding_ids: list[str]) -> list[dict]:
        all_findings: list[dict] = []
        for i in range(0, len(finding_ids), BATCH_SIZE):
            batch = finding_ids[i: i + BATCH_SIZE]

            def _get(b=batch):
                return self.client.get_findings(
                    DetectorId=detector_id,
                    FindingIds=b,
                )

            response = await self._run_sync(_get)
            all_findings.extend(response.get("Findings", []))

        logger.info(
            "GuardDuty: fetched %d findings from account=%s",
            len(all_findings), self.account_id,
        )
        return all_findings
