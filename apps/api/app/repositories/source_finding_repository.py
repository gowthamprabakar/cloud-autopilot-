"""
Source Finding Repository — data access for source_findings table.

Upsert semantics: (aws_account_id, native_finding_id) is the uniqueness key.
On conflict, update severity + title + description + last_observed_at + raw_payload.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.enums import FindingSeverity, FindingSource
from app.models.source_finding import SourceFinding
from app.repositories.base import BaseRepository


class SourceFindingRepository(BaseRepository[SourceFinding]):
    model = SourceFinding

    async def upsert(
        self,
        *,
        aws_account_id: uuid.UUID,
        workspace_id: uuid.UUID,
        source: FindingSource,
        native_finding_id: str,
        severity: FindingSeverity,
        title: str,
        description: str | None,
        raw_payload: dict,
        region: str | None,
        resource_arn: str | None,
        resource_type: str | None,
        first_observed_at: str | None,
        last_observed_at: str | None,
    ) -> SourceFinding:
        """
        Insert or update a source finding by (aws_account_id, native_finding_id).

        Uses SQLAlchemy ORM for SQLite compat (no ON CONFLICT in SQLite syntax
        via raw SQL). For Postgres production, this is replaced with pg_insert
        on_conflict_do_update in Phase 4.

        Phase 3: ORM-based upsert (check-then-insert/update).
        """
        now = datetime.now(UTC)

        existing = await self.db.execute(
            select(SourceFinding).where(
                SourceFinding.aws_account_id == aws_account_id,
                SourceFinding.native_finding_id == native_finding_id,
            )
        )
        finding = existing.scalar_one_or_none()

        if finding is None:
            finding = SourceFinding(
                aws_account_id=aws_account_id,
                workspace_id=workspace_id,
                source=source,
                native_finding_id=native_finding_id,
                severity=severity,
                title=title,
                description=description,
                raw_payload=raw_payload,
                region=region,
                resource_arn=resource_arn,
                resource_type=resource_type,
                first_observed_at=first_observed_at,
                last_observed_at=last_observed_at,
            )
            self.db.add(finding)
            await self.db.flush()
            await self.db.refresh(finding)
        else:
            # Update mutable fields
            finding.severity = severity
            finding.title = title
            finding.description = description
            finding.raw_payload = raw_payload
            finding.last_observed_at = last_observed_at
            self.db.add(finding)
            await self.db.flush()

        return finding

    async def list_unnormalized(
        self, aws_account_id: uuid.UUID, limit: int = 500
    ) -> list[SourceFinding]:
        """Return source findings not yet linked to a canonical finding."""
        result = await self.db.execute(
            select(SourceFinding)
            .where(
                SourceFinding.aws_account_id == aws_account_id,
                SourceFinding.canonical_finding_id.is_(None),
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_account(self, aws_account_id: uuid.UUID) -> int:
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count()).where(SourceFinding.aws_account_id == aws_account_id)
        )
        return result.scalar_one()
