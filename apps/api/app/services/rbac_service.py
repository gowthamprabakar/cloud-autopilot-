"""
RBACService — Role-Based Access Control for OmniSec.

Sprint 32: Enforces tenant isolation and role-based permissions.

Roles:
  - super_admin: Full platform access, manage tenants
  - admin: Full workspace access, manage team + settings
  - analyst: Run simulations, view all dashboards, manage findings
  - viewer: Read-only access to dashboards and reports
  - api_only: Programmatic access via API keys only

Permissions matrix:
  - simulations.run: admin, analyst
  - simulations.view: admin, analyst, viewer
  - simulations.delete: admin
  - findings.manage: admin, analyst
  - findings.view: admin, analyst, viewer
  - settings.manage: admin
  - team.manage: admin
  - agents.spawn: admin, analyst
  - graph.query: admin, analyst
  - graph.ingest: admin
  - memory.view: admin, analyst
  - memory.manage: admin
  - reports.generate: admin, analyst
  - reports.view: admin, analyst, viewer
  - integrations.manage: admin
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.simulation_run import SimulationRun
from app.models.tenant_config import TenantConfig


class RBACService:
    """Centralised RBAC + tenant-config service."""

    # permission -> set of roles that may exercise it
    PERMISSIONS: dict[str, set[str]] = {
        "simulations.run": {"super_admin", "admin", "analyst"},
        "simulations.view": {"super_admin", "admin", "analyst", "viewer"},
        "simulations.delete": {"super_admin", "admin"},
        "findings.manage": {"super_admin", "admin", "analyst"},
        "findings.view": {"super_admin", "admin", "analyst", "viewer"},
        "settings.manage": {"super_admin", "admin"},
        "team.manage": {"super_admin", "admin"},
        "agents.spawn": {"super_admin", "admin", "analyst"},
        "graph.query": {"super_admin", "admin", "analyst"},
        "graph.ingest": {"super_admin", "admin"},
        "memory.view": {"super_admin", "admin", "analyst"},
        "memory.manage": {"super_admin", "admin"},
        "reports.generate": {"super_admin", "admin", "analyst"},
        "reports.view": {"super_admin", "admin", "analyst", "viewer"},
        "integrations.manage": {"super_admin", "admin"},
    }

    # Map feature flag column names to user-facing feature names
    _FEATURE_FLAG_MAP: dict[str, str] = {
        "simulations": "feature_simulations",
        "graph_explorer": "feature_graph_explorer",
        "agent_memory": "feature_agent_memory",
        "ciem": "feature_ciem",
        "vulns": "feature_vulns",
        "detections": "feature_detections",
    }

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Permission checks ─────────────────────────────────────────

    def check_permission(self, user_role: str, permission: str) -> bool:
        """
        Check if a role has a specific permission.
        Raises ForbiddenError if the role is not allowed.
        Returns True on success.
        """
        allowed_roles = self.PERMISSIONS.get(permission)
        if allowed_roles is None:
            raise ForbiddenError(f"Unknown permission: {permission}")
        if user_role not in allowed_roles:
            raise ForbiddenError(
                f"Role '{user_role}' lacks permission '{permission}'"
            )
        return True

    async def get_user_permissions(self, user_role: str) -> list[str]:
        """Return all permissions granted to a given role."""
        return sorted(
            perm
            for perm, roles in self.PERMISSIONS.items()
            if user_role in roles
        )

    # ── Tenant configuration ──────────────────────────────────────

    async def get_tenant_config(self, tenant_id: uuid.UUID) -> TenantConfig | None:
        """Get tenant configuration with feature flags."""
        result = await self.db.execute(
            select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def check_feature_enabled(self, tenant_id: uuid.UUID, feature: str) -> bool:
        """
        Check if a feature is enabled for a tenant.
        Raises ForbiddenError if the feature is disabled.
        Returns True if enabled.
        """
        column_name = self._FEATURE_FLAG_MAP.get(feature)
        if column_name is None:
            raise ForbiddenError(f"Unknown feature: {feature}")

        config = await self.get_tenant_config(tenant_id)
        if config is None:
            # No config row means all features default to enabled
            return True

        enabled = getattr(config, column_name, True)
        if not enabled:
            raise ForbiddenError(
                f"Feature '{feature}' is disabled for this tenant"
            )
        return True

    async def check_simulation_budget(self, tenant_id: uuid.UUID) -> dict:
        """
        Check simulation count and API budget against tenant limits.
        Returns a dict with current usage vs limits.
        """
        config = await self.get_tenant_config(tenant_id)
        if config is None:
            return {
                "simulations_this_month": 0,
                "max_simulations_per_month": 100,
                "simulations_remaining": 100,
                "total_cost_usd": 0.0,
                "api_budget_usd": 500.0,
                "budget_remaining_usd": 500.0,
                "within_budget": True,
            }

        # Count simulations created this calendar month for the tenant's
        # workspaces. We join through the workspace table implicitly by
        # checking workspace_id belongs to this tenant via SimulationRun.
        now = datetime.now(UTC)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Get workspaces for this tenant
        from app.models.workspace import Workspace

        ws_result = await self.db.execute(
            select(Workspace.id).where(Workspace.tenant_id == tenant_id)
        )
        workspace_ids = [row[0] for row in ws_result.fetchall()]

        sim_count = 0
        total_cost = 0.0

        if workspace_ids:
            count_result = await self.db.execute(
                select(func.count(SimulationRun.id)).where(
                    SimulationRun.workspace_id.in_(workspace_ids),
                    SimulationRun.created_at >= month_start,
                )
            )
            sim_count = count_result.scalar_one() or 0

            cost_result = await self.db.execute(
                select(func.coalesce(func.sum(SimulationRun.total_cost_usd), 0.0)).where(
                    SimulationRun.workspace_id.in_(workspace_ids),
                    SimulationRun.created_at >= month_start,
                )
            )
            total_cost = float(cost_result.scalar_one() or 0.0)

        max_sims = config.max_simulations_per_month
        budget = config.api_budget_usd

        return {
            "simulations_this_month": sim_count,
            "max_simulations_per_month": max_sims,
            "simulations_remaining": max(0, max_sims - sim_count),
            "total_cost_usd": round(total_cost, 2),
            "api_budget_usd": budget,
            "budget_remaining_usd": round(max(0.0, budget - total_cost), 2),
            "within_budget": sim_count < max_sims and total_cost < budget,
        }

    # ── CRUD ──────────────────────────────────────────────────────

    async def create_tenant_config(
        self, tenant_id: uuid.UUID, config_data: dict
    ) -> TenantConfig:
        """Create tenant configuration."""
        tenant_config = TenantConfig(tenant_id=tenant_id, **config_data)
        self.db.add(tenant_config)
        await self.db.flush()
        await self.db.refresh(tenant_config)
        return tenant_config

    async def update_tenant_config(
        self, tenant_id: uuid.UUID, updates: dict
    ) -> TenantConfig:
        """Update tenant configuration (branding, features, limits)."""
        config = await self.get_tenant_config(tenant_id)
        if config is None:
            raise NotFoundError("Tenant configuration not found")

        # Filter to only valid column names
        valid_columns = {c.name for c in TenantConfig.__table__.columns}
        # Never allow updating id, tenant_id, created_at via this method
        immutable = {"id", "tenant_id", "created_at"}
        safe_updates = {
            k: v for k, v in updates.items()
            if k in valid_columns and k not in immutable
        }

        if safe_updates:
            await self.db.execute(
                update(TenantConfig)
                .where(TenantConfig.tenant_id == tenant_id)
                .values(**safe_updates)
            )
            await self.db.flush()
            await self.db.refresh(config)

        return config
