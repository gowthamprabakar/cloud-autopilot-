"""
TenantConfig — white-label branding + feature flags + usage limits.

Sprint 32: Multi-tenant RBAC system. Each tenant gets a configuration row
controlling branding (logo, colours, custom domain), feature flags, usage
limits (simulations, agents, API budget), and SSO provider settings.
"""

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class TenantConfig(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "tenant_configs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # ── White-label branding ──────────────────────────────────────
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    primary_color: Mapped[str] = mapped_column(String(9), nullable=False, default="#3B82F6")
    secondary_color: Mapped[str] = mapped_column(String(9), nullable=False, default="#1E293B")
    favicon_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    custom_domain: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True
    )  # e.g. security.acme.com

    # ── Feature flags ─────────────────────────────────────────────
    feature_simulations: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    feature_graph_explorer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    feature_agent_memory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    feature_ciem: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    feature_vulns: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    feature_detections: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── Usage limits ──────────────────────────────────────────────
    max_simulations_per_month: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100
    )
    max_agents_per_simulation: Mapped[int] = mapped_column(
        Integer, nullable=False, default=20
    )
    api_budget_usd: Mapped[float] = mapped_column(
        Float, nullable=False, default=500.0
    )

    # ── SSO configuration ─────────────────────────────────────────
    sso_provider: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # "auth0", "okta", "azure_ad", None
    sso_client_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sso_tenant_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sso_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<TenantConfig tenant_id={self.tenant_id} display_name={self.display_name}>"
