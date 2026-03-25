"""
Suppression Service — business logic for suppression rules.

Rules:
- workspace_id always scopes all operations.
- Soft-delete (is_active=False) on delete — never hard-delete.
- apply_rules_to_workspace matches OPEN findings against all active rules.
"""

import uuid

import structlog

from app.models.canonical_finding import CanonicalFinding
from app.models.enums import FindingStatus
from app.models.suppression_rule import SuppressionRule
from app.repositories.canonical_finding_repository import CanonicalFindingRepository
from app.repositories.suppression_rule_repository import SuppressionRuleRepository
from app.schemas.suppression_rule import SuppressionRuleCreate

logger = structlog.get_logger(__name__)


def _finding_matches_rule(finding: CanonicalFinding, rule: SuppressionRule) -> bool:
    """
    Return True if a finding matches ALL non-None conditions of a rule (AND logic).
    """
    if rule.match_title_contains is not None:
        if finding.title is None:
            return False
        if rule.match_title_contains.lower() not in finding.title.lower():
            return False

    if rule.match_resource_type is not None:
        if finding.resource_type != rule.match_resource_type:
            return False

    if rule.match_resource_arn_contains is not None:
        if finding.resource_arn is None:
            return False
        if rule.match_resource_arn_contains.lower() not in finding.resource_arn.lower():
            return False

    if rule.match_severity is not None:
        # Compare string values
        finding_severity = (
            finding.severity.value
            if hasattr(finding.severity, "value")
            else str(finding.severity)
        )
        if finding_severity != rule.match_severity:
            return False

    return True


class SuppressionService:
    def __init__(
        self,
        repo: SuppressionRuleRepository,
        finding_repo: CanonicalFindingRepository,
    ) -> None:
        self._repo = repo
        self._finding_repo = finding_repo

    async def list_rules(self, workspace_id: uuid.UUID) -> list[SuppressionRule]:
        """Return all suppression rules for a workspace."""
        return await self._repo.list_by_workspace(workspace_id)

    async def create_rule(
        self,
        workspace_id: uuid.UUID,
        created_by: uuid.UUID,
        data: SuppressionRuleCreate,
    ) -> SuppressionRule:
        """Create a new suppression rule for the workspace."""
        rule = SuppressionRule(
            workspace_id=workspace_id,
            created_by_user_id=created_by,
            name=data.name,
            reason=data.reason,
            match_title_contains=data.match_title_contains,
            match_resource_type=data.match_resource_type,
            match_resource_arn_contains=data.match_resource_arn_contains,
            match_severity=data.match_severity,
            is_active=True,
            expires_at=data.expires_at,
        )
        created = await self._repo.create(rule)
        logger.info(
            "suppression_rule.created",
            rule_id=str(created.id),
            workspace_id=str(workspace_id),
            name=data.name,
        )
        return created

    async def delete_rule(self, rule_id: uuid.UUID, workspace_id: uuid.UUID) -> None:
        """Soft-delete: set is_active=False. Raises NotFoundError if not found."""
        from app.core.exceptions import NotFoundError

        rule = await self._repo.get_by_workspace(rule_id, workspace_id)
        if rule is None:
            raise NotFoundError(f"SuppressionRule {rule_id} not found")
        await self._repo.update_fields(rule_id, is_active=False)
        logger.info(
            "suppression_rule.deleted",
            rule_id=str(rule_id),
            workspace_id=str(workspace_id),
        )

    async def apply_rules_to_workspace(self, workspace_id: uuid.UUID) -> int:
        """
        Apply all active suppression rules to OPEN findings in the workspace.
        For each active rule, find all OPEN findings that match ALL non-None conditions.
        Set matching findings status=SUPPRESSED.
        Returns count of suppressed findings.
        """
        rules = await self._repo.list_active_by_workspace(workspace_id)
        if not rules:
            logger.info("suppression.apply.no_active_rules", workspace_id=str(workspace_id))
            return 0

        # Load all OPEN findings for the workspace
        open_findings = await self._finding_repo.list_by_workspace(
            workspace_id=workspace_id,
            status=FindingStatus.OPEN,
            page=1,
            page_size=10000,  # large batch
        )

        suppressed_ids: set[uuid.UUID] = set()

        for rule in rules:
            for finding in open_findings:
                if finding.id not in suppressed_ids and _finding_matches_rule(finding, rule):
                    suppressed_ids.add(finding.id)

        # Apply suppression
        for fid in suppressed_ids:
            await self._finding_repo.update_fields(fid, status=FindingStatus.SUPPRESSED)

        count = len(suppressed_ids)
        logger.info(
            "suppression.apply.complete",
            workspace_id=str(workspace_id),
            suppressed=count,
            rules_applied=len(rules),
        )
        return count
