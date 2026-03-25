"""
Canonical Finding Repository — data access for canonical_findings table.
"""

import uuid

from sqlalchemy import func, select, text

from app.models.canonical_finding import CanonicalFinding
from app.models.enums import FindingSeverity, FindingSource, FindingStatus
from app.repositories.base import BaseRepository


class CanonicalFindingRepository(BaseRepository[CanonicalFinding]):
    model = CanonicalFinding

    async def get_by_id_and_workspace(
        self, finding_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> CanonicalFinding | None:
        result = await self.db.execute(
            select(CanonicalFinding).where(
                CanonicalFinding.id == finding_id,
                CanonicalFinding.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_fingerprint(
        self, fingerprint: str, workspace_id: uuid.UUID
    ) -> CanonicalFinding | None:
        result = await self.db.execute(
            select(CanonicalFinding).where(
                CanonicalFinding.fingerprint == fingerprint,
                CanonicalFinding.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        severity: FindingSeverity | None = None,
        status: FindingStatus | None = None,
        aws_account_id: uuid.UUID | None = None,
        order_by_risk_desc: bool = False,
        page: int = 1,
        page_size: int = 50,
    ) -> list[CanonicalFinding]:
        q = select(CanonicalFinding).where(
            CanonicalFinding.workspace_id == workspace_id
        )
        if severity:
            q = q.where(CanonicalFinding.severity == severity)
        if status:
            q = q.where(CanonicalFinding.status == status)
        if aws_account_id:
            q = q.where(CanonicalFinding.aws_account_id == aws_account_id)
        if order_by_risk_desc:
            q = q.order_by(CanonicalFinding.risk_score.desc().nullslast())
        else:
            q = q.order_by(CanonicalFinding.created_at.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def count_by_severity(
        self, workspace_id: uuid.UUID, status: FindingStatus = FindingStatus.OPEN
    ) -> dict[str, int]:
        """Return {severity: count} for dashboard widgets."""
        result = await self.db.execute(
            select(CanonicalFinding.severity, func.count())
            .where(
                CanonicalFinding.workspace_id == workspace_id,
                CanonicalFinding.status == status,
            )
            .group_by(CanonicalFinding.severity)
        )
        rows = result.all()
        counts = {sev.value: 0 for sev in FindingSeverity}
        for sev, cnt in rows:
            counts[sev] = cnt
        return counts

    async def count_by_workspace(
        self,
        workspace_id: uuid.UUID,
        severity: FindingSeverity | None = None,
        status: FindingStatus | None = None,
        aws_account_id: uuid.UUID | None = None,
    ) -> int:
        """Return total count for a workspace with optional filters."""
        q = select(func.count()).where(
            CanonicalFinding.workspace_id == workspace_id
        )
        if severity:
            q = q.where(CanonicalFinding.severity == severity)
        if status:
            q = q.where(CanonicalFinding.status == status)
        if aws_account_id:
            q = q.where(CanonicalFinding.aws_account_id == aws_account_id)
        result = await self.db.execute(q)
        return result.scalar_one()

    async def count_by_status(self, workspace_id: uuid.UUID) -> dict[str, int]:
        """Return {status: count} for all statuses in a workspace."""
        result = await self.db.execute(
            select(CanonicalFinding.status, func.count())
            .where(CanonicalFinding.workspace_id == workspace_id)
            .group_by(CanonicalFinding.status)
        )
        rows = result.all()
        counts = {st.value: 0 for st in FindingStatus}
        for st, cnt in rows:
            counts[st] = cnt
        return counts

    async def count_new_since(self, workspace_id: uuid.UUID, since_iso: str) -> int:
        """Count findings first seen at or after since_iso."""
        result = await self.db.execute(
            select(func.count()).where(
                CanonicalFinding.workspace_id == workspace_id,
                CanonicalFinding.first_seen_at >= since_iso,
            )
        )
        return result.scalar_one() or 0

    async def count_resolved_since(self, workspace_id: uuid.UUID, since_iso: str) -> int:
        """Count findings resolved at or after since_iso."""
        result = await self.db.execute(
            select(func.count()).where(
                CanonicalFinding.workspace_id == workspace_id,
                CanonicalFinding.resolved_at >= since_iso,
                CanonicalFinding.resolved_at.isnot(None),
            )
        )
        return result.scalar_one() or 0

    async def avg_risk_score(
        self, workspace_id: uuid.UUID, status: FindingStatus | None = None
    ) -> float | None:
        """Return average risk_score, optionally filtered by status."""
        q = select(func.avg(CanonicalFinding.risk_score)).where(
            CanonicalFinding.workspace_id == workspace_id,
            CanonicalFinding.risk_score.isnot(None),
        )
        if status is not None:
            q = q.where(CanonicalFinding.status == status)
        result = await self.db.execute(q)
        val = result.scalar_one()
        return float(val) if val is not None else None

    async def avg_resolution_days(self, workspace_id: uuid.UUID) -> float | None:
        """
        Mean time to resolve in days.
        Uses SQLite julianday() for the calculation.
        Returns None if no resolved findings with timestamps.
        """
        result = await self.db.execute(
            text(
                "SELECT AVG(julianday(resolved_at) - julianday(first_seen_at)) "
                "FROM canonical_findings "
                "WHERE workspace_id = :wid "
                "AND resolved_at IS NOT NULL AND first_seen_at IS NOT NULL"
            ),
            {"wid": str(workspace_id)},
        )
        val = result.scalar_one()
        return float(val) if val is not None else None

    async def compliance_framework_stats(self, workspace_id: uuid.UUID) -> dict:
        """
        Returns {framework_id: {"total": N, "passing": N}} for all frameworks
        found in compliance_frameworks JSON arrays across findings in this workspace.

        "passing" = finding has status RESOLVED or ACCEPTED (not open/suppressed).

        Implementation: load all findings' compliance_frameworks and status, compute in Python.
        Efficient enough for < 100k findings.
        """
        result = await self.db.execute(
            select(
                CanonicalFinding.compliance_frameworks,
                CanonicalFinding.status,
            ).where(CanonicalFinding.workspace_id == workspace_id)
        )
        rows = result.all()

        stats: dict[str, dict] = {}
        passing_statuses = {FindingStatus.RESOLVED.value, FindingStatus.ACCEPTED.value}

        for frameworks, status in rows:
            if not frameworks:
                continue
            is_passing = status in passing_statuses
            for fw in frameworks:
                if fw not in stats:
                    stats[fw] = {"total": 0, "passing": 0}
                stats[fw]["total"] += 1
                if is_passing:
                    stats[fw]["passing"] += 1

        return stats
