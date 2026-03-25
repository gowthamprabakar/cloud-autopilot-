"""
SuppressionRule Repository — data access for suppression_rules table.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.models.suppression_rule import SuppressionRule
from app.repositories.base import BaseRepository


class SuppressionRuleRepository(BaseRepository[SuppressionRule]):
    model = SuppressionRule

    async def list_by_workspace(self, workspace_id: uuid.UUID) -> list[SuppressionRule]:
        """Return all rules (active and inactive) for the workspace."""
        result = await self.db.execute(
            select(SuppressionRule)
            .where(SuppressionRule.workspace_id == workspace_id)
            .order_by(SuppressionRule.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_active_by_workspace(self, workspace_id: uuid.UUID) -> list[SuppressionRule]:
        """Return active rules where is_active=True and (expires_at is None OR expires_at > now)."""
        now_iso = datetime.now(UTC).isoformat()
        result = await self.db.execute(
            select(SuppressionRule).where(
                SuppressionRule.workspace_id == workspace_id,
                SuppressionRule.is_active == True,  # noqa: E712
            )
        )
        rules = list(result.scalars().all())
        # Filter out expired rules in Python (expires_at is a string column)
        active = []
        for rule in rules:
            if rule.expires_at is None:
                active.append(rule)
            else:
                try:
                    exp = datetime.fromisoformat(rule.expires_at.replace("Z", "+00:00"))
                    if exp.tzinfo is None:
                        from datetime import timezone
                        exp = exp.replace(tzinfo=timezone.utc)
                    if exp > datetime.now(UTC):
                        active.append(rule)
                except (ValueError, TypeError):
                    # Malformed expires_at — treat as non-expired (safe default)
                    active.append(rule)
        return active

    async def get_by_workspace(
        self, rule_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> SuppressionRule | None:
        """Fetch a rule by ID with workspace ownership check."""
        result = await self.db.execute(
            select(SuppressionRule).where(
                SuppressionRule.id == rule_id,
                SuppressionRule.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()
