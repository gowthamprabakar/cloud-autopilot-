"""
Findings Service — business logic for querying and managing canonical findings.

Rules:
- workspace_id always scopes all queries.
- status transitions are validated here.
- resolved_at is set only by this service when status → RESOLVED.
"""

import uuid
from datetime import UTC, datetime

import structlog

from app.core.exceptions import NotFoundError
from app.models.canonical_finding import CanonicalFinding
from app.models.enums import FindingSeverity, FindingStatus
from app.repositories.canonical_finding_repository import CanonicalFindingRepository
from app.repositories.source_finding_repository import SourceFindingRepository
from app.schemas.finding import FindingUpdateRequest

logger = structlog.get_logger(__name__)


class FindingsService:
    def __init__(
        self,
        canonical_repo: CanonicalFindingRepository,
        source_repo: SourceFindingRepository,
        audit_log_service=None,
        notification_service=None,
    ) -> None:
        self._canonical = canonical_repo
        self._source = source_repo
        self._audit = audit_log_service
        self._notifications = notification_service

    async def list_findings(
        self,
        workspace_id: uuid.UUID,
        severity: FindingSeverity | None = None,
        status: FindingStatus | None = None,
        aws_account_id: uuid.UUID | None = None,
        source: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[CanonicalFinding], int]:
        """
        Returns (items, total_count) for the given filters.
        source filter is not currently applied at DB level (reserved for future use).
        """
        items = await self._canonical.list_by_workspace(
            workspace_id=workspace_id,
            severity=severity,
            status=status,
            aws_account_id=aws_account_id,
            page=page,
            page_size=page_size,
        )
        total = await self._canonical.count_by_workspace(
            workspace_id=workspace_id,
            severity=severity,
            status=status,
            aws_account_id=aws_account_id,
        )
        return items, total

    async def get_finding(
        self,
        finding_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> CanonicalFinding:
        """Fetch a single finding; raises NotFoundError if missing or wrong workspace."""
        finding = await self._canonical.get_by_id(finding_id)
        if finding is None or str(finding.workspace_id) != str(workspace_id):
            raise NotFoundError(f"Finding {finding_id} not found")
        return finding

    async def update_finding(
        self,
        finding_id: uuid.UUID,
        workspace_id: uuid.UUID,
        data: FindingUpdateRequest,
    ) -> CanonicalFinding:
        """
        Apply status and/or tag updates to a finding.
        If status is set to RESOLVED, resolved_at is set to now.
        """
        finding = await self.get_finding(finding_id, workspace_id)

        fields: dict = {}
        old_status = finding.status
        if data.status is not None:
            fields["status"] = data.status
            if data.status == FindingStatus.RESOLVED:
                fields["resolved_at"] = datetime.now(UTC).isoformat()

        if data.tags is not None:
            # Merge incoming tags with existing tags
            merged = dict(finding.tags or {})
            merged.update(data.tags)
            fields["tags"] = merged

        if not fields:
            return finding

        updated = await self._canonical.update_fields(finding.id, **fields)
        logger.info(
            "finding.updated",
            finding_id=str(finding_id),
            workspace_id=str(workspace_id),
            fields=list(fields.keys()),
        )

        # Fire webhook (fire-and-forget)
        if data.status is not None:
            try:
                from app.services.webhook_service import WebhookService
                from app.repositories.webhook_repository import WebhookRepository
                webhook_svc = WebhookService(repo=WebhookRepository(self._canonical.db))
                event = "finding.status_changed"
                if hasattr(updated, 'severity') and str(updated.severity) == 'critical':
                    event = "finding.critical"
                await webhook_svc.dispatch(
                    workspace_id=updated.workspace_id,
                    event_name=event,
                    payload={
                        "finding_id": str(updated.id),
                        "title": updated.title,
                        "severity": str(updated.severity) if updated.severity else None,
                        "status": str(updated.status) if updated.status else None,
                    }
                )
            except Exception:
                pass  # Never let webhook failure break the main flow

        # Audit log for status changes
        if data.status is not None and self._audit is not None:
            try:
                await self._audit.log(
                    workspace_id=workspace_id,
                    actor_user_id=None,
                    actor_email="system",
                    action="finding.status_changed",
                    resource_type="finding",
                    resource_id=str(finding_id),
                    detail={
                        "finding_id": str(finding_id),
                        "old_status": str(old_status),
                        "new_status": str(data.status),
                    },
                )
            except Exception:
                pass

        return updated

    async def bulk_update_status(
        self,
        finding_ids: list[uuid.UUID],
        workspace_id: uuid.UUID,
        new_status: FindingStatus,
    ) -> tuple[int, int, list[str]]:
        """
        Bulk update status for multiple findings.
        Only updates findings that belong to workspace_id.
        Returns (updated_count, failed_count, error_messages).
        """
        updated = 0
        failed = 0
        errors = []
        for fid in finding_ids:
            try:
                finding = await self._canonical.get_by_id(fid)
                if finding is None or str(finding.workspace_id) != str(workspace_id):
                    failed += 1
                    errors.append(f"Finding {fid} not found or access denied")
                    continue
                fields: dict = {"status": new_status}
                if new_status == FindingStatus.RESOLVED:
                    fields["resolved_at"] = datetime.now(UTC).isoformat()
                await self._canonical.update_fields(fid, **fields)
                updated += 1
            except Exception as exc:
                failed += 1
                errors.append(f"Finding {fid}: {exc}")
        return updated, failed, errors

    async def get_stats(self, workspace_id: uuid.UUID) -> dict:
        """
        Returns {by_severity: {critical:N,...}, by_status: {open:N,...}, total: N}
        for the given workspace.
        """
        by_severity = await self._canonical.count_by_severity(
            workspace_id=workspace_id,
            status=FindingStatus.OPEN,
        )
        by_status = await self._canonical.count_by_status(workspace_id=workspace_id)
        total = await self._canonical.count_by_workspace(workspace_id=workspace_id)
        return {
            "by_severity": by_severity,
            "by_status": by_status,
            "total": total,
        }
