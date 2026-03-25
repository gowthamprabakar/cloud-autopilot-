"""
Report Service — generates executive summary and export data.
Reads only — never writes any data.
"""

import uuid
from datetime import UTC, datetime, timedelta

import structlog

from app.repositories.aws_account_repository import AwsAccountRepository
from app.repositories.canonical_finding_repository import CanonicalFindingRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.report import (
    AccountSummary,
    ComplianceSummary,
    ExecutiveSummaryResponse,
)

logger = structlog.get_logger(__name__)


class ReportService:
    def __init__(
        self,
        finding_repo: CanonicalFindingRepository,
        account_repo: AwsAccountRepository,
        workspace_repo: WorkspaceRepository,
    ) -> None:
        self._findings = finding_repo
        self._accounts = account_repo
        self._workspaces = workspace_repo

    async def executive_summary(
        self, workspace_id: uuid.UUID, period_days: int = 30
    ) -> ExecutiveSummaryResponse:
        """Generate executive summary for the workspace."""
        from app.models.enums import FindingSeverity, FindingStatus

        now = datetime.now(UTC)
        seven_days_ago = (now - timedelta(days=7)).isoformat()

        # Total findings
        total = await self._findings.count_by_workspace(workspace_id=workspace_id)
        open_total = await self._findings.count_by_workspace(
            workspace_id=workspace_id, status=FindingStatus.OPEN
        )
        critical_open = await self._findings.count_by_workspace(
            workspace_id=workspace_id,
            severity=FindingSeverity.CRITICAL,
            status=FindingStatus.OPEN,
        )
        high_open = await self._findings.count_by_workspace(
            workspace_id=workspace_id,
            severity=FindingSeverity.HIGH,
            status=FindingStatus.OPEN,
        )

        # New in last 7 days — count findings where first_seen_at >= 7 days ago
        new_7d = await self._findings.count_new_since(workspace_id, seven_days_ago)
        resolved_7d = await self._findings.count_resolved_since(workspace_id, seven_days_ago)

        # Average risk score (open findings only)
        avg_risk = await self._findings.avg_risk_score(
            workspace_id, status=FindingStatus.OPEN
        )

        # MTTR — mean time to resolve in days
        mttr = await self._findings.avg_resolution_days(workspace_id)

        # Top 10 riskiest open findings
        top_items = await self._findings.list_by_workspace(
            workspace_id=workspace_id,
            status=FindingStatus.OPEN,
            order_by_risk_desc=True,
            page=1,
            page_size=10,
        )
        top_findings = [
            {
                "id": str(f.id),
                "title": f.title,
                "severity": f.severity,
                "risk_score": f.risk_score,
                "resource_type": f.resource_type,
                "resource_arn": f.resource_arn,
            }
            for f in top_items
        ]

        # Per-account breakdown
        accounts = await self._accounts.list_by_workspace(workspace_id)
        account_summaries = []
        for acct in accounts:
            acct_total = await self._findings.count_by_workspace(
                workspace_id=workspace_id, aws_account_id=acct.id
            )
            acct_open = await self._findings.count_by_workspace(
                workspace_id=workspace_id,
                aws_account_id=acct.id,
                status=FindingStatus.OPEN,
            )
            acct_crit = await self._findings.count_by_workspace(
                workspace_id=workspace_id,
                aws_account_id=acct.id,
                severity=FindingSeverity.CRITICAL,
                status=FindingStatus.OPEN,
            )
            account_summaries.append(AccountSummary(
                account_id=acct.account_id,
                account_alias=acct.account_alias,
                total_findings=acct_total,
                open_findings=acct_open,
                critical_findings=acct_crit,
            ))

        # Compliance summary — count by framework from compliance_frameworks JSON
        compliance_data = await self._findings.compliance_framework_stats(workspace_id)
        compliance = [
            ComplianceSummary(
                framework_id=fw,
                total=stats["total"],
                passing=stats["passing"],
                coverage_pct=round(
                    100.0 * stats["passing"] / stats["total"] if stats["total"] else 0.0,
                    1,
                ),
            )
            for fw, stats in compliance_data.items()
        ]

        return ExecutiveSummaryResponse(
            generated_at=now.isoformat(),
            workspace_id=str(workspace_id),
            period_days=period_days,
            total_findings=total,
            open_findings=open_total,
            critical_open=critical_open,
            high_open=high_open,
            new_last_7_days=new_7d,
            resolved_last_7_days=resolved_7d,
            avg_risk_score=round(avg_risk, 2) if avg_risk is not None else None,
            mttr_days=round(mttr, 1) if mttr is not None else None,
            top_findings=top_findings,
            accounts=account_summaries,
            compliance=compliance,
        )
