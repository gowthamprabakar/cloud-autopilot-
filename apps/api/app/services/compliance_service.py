"""
Compliance Service — computes coverage stats per compliance framework.

For each framework found in canonical_findings.compliance_frameworks,
computes: total findings mapped, open vs resolved count, coverage_pct.
"""

import uuid
from datetime import UTC, datetime

import structlog

from app.models.enums import FindingStatus
from app.repositories.canonical_finding_repository import CanonicalFindingRepository
from app.schemas.compliance import FRAMEWORK_DISPLAY_NAMES

logger = structlog.get_logger(__name__)


class ComplianceService:
    def __init__(self, canonical_repo: CanonicalFindingRepository) -> None:
        self._canonical = canonical_repo

    async def get_compliance_stats(self, workspace_id: uuid.UUID) -> dict:
        """
        Aggregate compliance coverage per framework.

        For each framework found in any canonical finding's compliance_frameworks:
          - total = total findings tagged with that framework
          - passing = resolved findings (status == RESOLVED)
          - failing = open/non-resolved findings
          - coverage_pct = passing / total * 100

        Returns: {frameworks: [...], last_updated: ISO string | None}
        """
        # Pull all findings for this workspace (no pagination — we need aggregate counts)
        # For large workspaces this should be moved to a dedicated DB query.
        # Phase 3: iterate in pages to avoid memory pressure.
        page = 1
        page_size = 500
        all_findings = []

        while True:
            batch = await self._canonical.list_by_workspace(
                workspace_id=workspace_id,
                page=page,
                page_size=page_size,
            )
            all_findings.extend(batch)
            if len(batch) < page_size:
                break
            page += 1

        if not all_findings:
            return {"frameworks": [], "last_updated": None}

        # Aggregate per framework
        framework_totals: dict[str, int] = {}
        framework_passing: dict[str, int] = {}

        for finding in all_findings:
            for fw_id in (finding.compliance_frameworks or []):
                framework_totals[fw_id] = framework_totals.get(fw_id, 0) + 1
                if finding.status == FindingStatus.RESOLVED:
                    framework_passing[fw_id] = framework_passing.get(fw_id, 0) + 1

        frameworks = []
        for fw_id, total in sorted(framework_totals.items()):
            passing = framework_passing.get(fw_id, 0)
            failing = total - passing
            coverage_pct = round((passing / total * 100), 2) if total > 0 else 0.0
            display_name = FRAMEWORK_DISPLAY_NAMES.get(fw_id, fw_id)
            frameworks.append(
                {
                    "framework_id": fw_id,
                    "display_name": display_name,
                    "total_controls": total,
                    "passing": passing,
                    "failing": failing,
                    "coverage_pct": coverage_pct,
                }
            )

        last_updated = datetime.now(UTC).isoformat()
        logger.info(
            "compliance.stats_computed",
            workspace_id=str(workspace_id),
            framework_count=len(frameworks),
        )
        return {"frameworks": frameworks, "last_updated": last_updated}
