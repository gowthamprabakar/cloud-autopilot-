"""Service for building and sending executive digest reports."""
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.canonical_finding_repository import CanonicalFindingRepository
from app.repositories.report_schedule_repository import ReportScheduleRepository
from app.services.email_service import EmailService
from app.services.email_templates import digest_email


class DigestService:
    def __init__(self, db: AsyncSession, email_service: EmailService | None = None):
        self.db = db
        self.finding_repo = CanonicalFindingRepository(db)
        self.schedule_repo = ReportScheduleRepository(db)
        self.email_svc = email_service or EmailService()

    async def build_digest_data(self, workspace_id: str) -> dict:
        """Build summary stats for the workspace digest."""
        import uuid as _uuid
        from app.models.enums import FindingStatus, FindingSeverity

        ws_id = _uuid.UUID(workspace_id)

        total_open = await self.finding_repo.count_by_workspace(
            workspace_id=ws_id, status=FindingStatus.OPEN
        )
        critical = await self.finding_repo.count_by_workspace(
            workspace_id=ws_id, severity=FindingSeverity.CRITICAL, status=FindingStatus.OPEN
        )
        high = await self.finding_repo.count_by_workspace(
            workspace_id=ws_id, severity=FindingSeverity.HIGH, status=FindingStatus.OPEN
        )
        medium = await self.finding_repo.count_by_workspace(
            workspace_id=ws_id, severity=FindingSeverity.MEDIUM, status=FindingStatus.OPEN
        )
        low = await self.finding_repo.count_by_workspace(
            workspace_id=ws_id, severity=FindingSeverity.LOW, status=FindingStatus.OPEN
        )

        from datetime import timedelta
        seven_days_ago = (datetime.now(UTC) - timedelta(days=7)).isoformat()
        resolved_this_week = await self.finding_repo.count_resolved_since(ws_id, seven_days_ago)

        top_items = await self.finding_repo.list_by_workspace(
            workspace_id=ws_id,
            status=FindingStatus.OPEN,
            order_by_risk_desc=True,
            page=1,
            page_size=5,
        )

        return {
            "total_open": total_open,
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
            "resolved_this_week": resolved_this_week,
            "top_findings": [
                {
                    "title": f.title,
                    "severity": f.severity.value if f.severity else "unknown",
                    "account": str(f.aws_account_id) if f.aws_account_id else "unknown",
                }
                for f in top_items
            ],
        }

    async def send_digest(self, workspace_id: str, recipients: list[str]) -> int:
        """Build and send digest to all recipients. Returns count sent."""
        if not recipients:
            return 0

        data = await self.build_digest_data(workspace_id)
        subject, html_body, text_body = digest_email(
            workspace_name=workspace_id,
            total_open=data["total_open"],
            critical=data["critical"],
            high=data["high"],
            medium=data["medium"],
            low=data["low"],
            resolved_this_week=data["resolved_this_week"],
            top_findings=data["top_findings"],
        )

        sent = 0
        for recipient in recipients:
            ok = await self.email_svc.send(
                to_email=recipient,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
            if ok:
                sent += 1
        return sent
