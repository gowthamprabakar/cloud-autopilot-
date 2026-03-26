"""
Tenant admin router — RBAC + branding + feature flags + budget (Sprint 32).

GET  /api/v1/admin/tenants/config       Get current tenant config
PUT  /api/v1/admin/tenants/config       Update tenant config (branding, features, limits)
GET  /api/v1/admin/tenants/budget       Check budget usage
GET  /api/v1/admin/tenants/permissions  List all permissions for current user role
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.enums import UserRole
from app.services.rbac_service import RBACService

router = APIRouter(prefix="/admin/tenants", tags=["tenant-admin"])

_ADMIN_ROLES = {UserRole.SUPER_ADMIN, UserRole.ADMIN}


def _require_admin(user: CurrentUserDep) -> None:
    """Guard — only super_admin or admin may access these endpoints."""
    if user.role not in _ADMIN_ROLES:
        raise ForbiddenError("Requires super_admin or admin role")


# ── Pydantic schemas ──────────────────────────────────────────────

class TenantConfigUpdate(BaseModel):
    display_name: str | None = None
    logo_url: str | None = None
    primary_color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary_color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    favicon_url: str | None = None
    custom_domain: str | None = None
    # Feature flags
    feature_simulations: bool | None = None
    feature_graph_explorer: bool | None = None
    feature_agent_memory: bool | None = None
    feature_ciem: bool | None = None
    feature_vulns: bool | None = None
    feature_detections: bool | None = None
    # Limits
    max_simulations_per_month: int | None = Field(None, ge=1)
    max_agents_per_simulation: int | None = Field(None, ge=1, le=100)
    api_budget_usd: float | None = Field(None, ge=0.0)
    # SSO
    sso_provider: str | None = None
    sso_client_id: str | None = None
    sso_tenant_id: str | None = None
    sso_domain: str | None = None


class TenantConfigResponse(BaseModel):
    tenant_id: str
    display_name: str
    logo_url: str | None = None
    primary_color: str
    secondary_color: str
    favicon_url: str | None = None
    custom_domain: str | None = None
    feature_simulations: bool
    feature_graph_explorer: bool
    feature_agent_memory: bool
    feature_ciem: bool
    feature_vulns: bool
    feature_detections: bool
    max_simulations_per_month: int
    max_agents_per_simulation: int
    api_budget_usd: float
    sso_provider: str | None = None
    sso_domain: str | None = None

    model_config = {"from_attributes": True}


# ── Endpoints ─────────────────────────────────────────────────────


@router.get("/config", summary="Get current tenant config")
async def get_tenant_config(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> TenantConfigResponse:
    _require_admin(current_user)
    svc = RBACService(db)
    config = await svc.get_tenant_config(current_user.tenant_id)
    if config is None:
        raise NotFoundError("Tenant configuration not found — run initial setup first")
    return TenantConfigResponse(
        tenant_id=str(config.tenant_id),
        display_name=config.display_name,
        logo_url=config.logo_url,
        primary_color=config.primary_color,
        secondary_color=config.secondary_color,
        favicon_url=config.favicon_url,
        custom_domain=config.custom_domain,
        feature_simulations=config.feature_simulations,
        feature_graph_explorer=config.feature_graph_explorer,
        feature_agent_memory=config.feature_agent_memory,
        feature_ciem=config.feature_ciem,
        feature_vulns=config.feature_vulns,
        feature_detections=config.feature_detections,
        max_simulations_per_month=config.max_simulations_per_month,
        max_agents_per_simulation=config.max_agents_per_simulation,
        api_budget_usd=config.api_budget_usd,
        sso_provider=config.sso_provider,
        sso_domain=config.sso_domain,
    )


@router.put("/config", summary="Update tenant config")
async def update_tenant_config(
    body: TenantConfigUpdate,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> TenantConfigResponse:
    _require_admin(current_user)
    svc = RBACService(db)

    # If config does not exist yet, create it
    existing = await svc.get_tenant_config(current_user.tenant_id)
    if existing is None:
        create_data = body.model_dump(exclude_none=True)
        if "display_name" not in create_data:
            create_data["display_name"] = "My Organisation"
        config = await svc.create_tenant_config(
            current_user.tenant_id, create_data
        )
    else:
        updates = body.model_dump(exclude_none=True)
        config = await svc.update_tenant_config(current_user.tenant_id, updates)

    return TenantConfigResponse(
        tenant_id=str(config.tenant_id),
        display_name=config.display_name,
        logo_url=config.logo_url,
        primary_color=config.primary_color,
        secondary_color=config.secondary_color,
        favicon_url=config.favicon_url,
        custom_domain=config.custom_domain,
        feature_simulations=config.feature_simulations,
        feature_graph_explorer=config.feature_graph_explorer,
        feature_agent_memory=config.feature_agent_memory,
        feature_ciem=config.feature_ciem,
        feature_vulns=config.feature_vulns,
        feature_detections=config.feature_detections,
        max_simulations_per_month=config.max_simulations_per_month,
        max_agents_per_simulation=config.max_agents_per_simulation,
        api_budget_usd=config.api_budget_usd,
        sso_provider=config.sso_provider,
        sso_domain=config.sso_domain,
    )


@router.get("/budget", summary="Check simulation budget usage")
async def get_budget(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    _require_admin(current_user)
    svc = RBACService(db)
    return await svc.check_simulation_budget(current_user.tenant_id)


@router.get("/permissions", summary="List permissions for current user role")
async def get_permissions(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return all permissions granted to the caller's role."""
    svc = RBACService(db)
    perms = await svc.get_user_permissions(current_user.role)
    return {
        "role": current_user.role,
        "permissions": perms,
        "total": len(perms),
    }
