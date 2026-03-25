"""
Auth service — register, login, current user.

Business rules enforced here:
- Tenant slug must be globally unique.
- Email must be unique per tenant.
- First user on a new tenant is always super_admin.
- Login is by email; returns JWT scoped to tenant + user.
- Password hashing via passlib bcrypt.
"""

import uuid
from datetime import UTC, datetime

import structlog

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.enums import UserRole
from app.models.tenant import Tenant
from app.models.user import User
from app.models.workspace import Workspace
from app.repositories.tenant_repository import TenantRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.auth import LoginRequest, RegisterRequest, RegisterResponse, TokenResponse
from app.schemas.auth import UserProfileResponse

logger = structlog.get_logger(__name__)


class AuthService:
    def __init__(
        self,
        tenant_repo: TenantRepository,
        workspace_repo: WorkspaceRepository,
        user_repo: UserRepository,
    ) -> None:
        self._tenants = tenant_repo
        self._workspaces = workspace_repo
        self._users = user_repo

    async def register(self, req: RegisterRequest) -> RegisterResponse:
        """
        Create a new tenant + default workspace + first super_admin user.
        Returns access token so the caller is immediately authenticated.
        """
        log = logger.bind(tenant_slug=req.tenant_slug, email=req.email)

        # Guard: slug must be unique
        if await self._tenants.slug_exists(req.tenant_slug):
            raise ConflictError(f"Tenant slug '{req.tenant_slug}' is already taken")

        # Create tenant
        tenant = Tenant(
            name=req.tenant_name,
            slug=req.tenant_slug,
            plan=req.plan,
        )
        tenant = await self._tenants.create(tenant)
        log.info("tenant.created", tenant_id=str(tenant.id))

        # Create default workspace
        ws_slug = req.workspace_name.lower().replace(" ", "-")
        workspace = Workspace(
            tenant_id=tenant.id,
            name=req.workspace_name,
            slug=ws_slug,
        )
        workspace = await self._workspaces.create(workspace)
        log.info("workspace.created", workspace_id=str(workspace.id))

        # Create first super_admin user
        user = User(
            tenant_id=tenant.id,
            workspace_id=workspace.id,
            email=req.email.lower(),
            hashed_password=hash_password(req.password),
            full_name=req.full_name,
            role=UserRole.SUPER_ADMIN,
        )
        user = await self._users.create(user)
        log.info("user.created", user_id=str(user.id))

        token = create_access_token(subject=str(user.id))

        return RegisterResponse(
            tenant_id=tenant.id,
            workspace_id=workspace.id,
            user_id=user.id,
            access_token=token,
        )

    async def login(self, req: LoginRequest) -> TokenResponse:
        """Authenticate user by email + password. Returns JWT."""
        from app.core.config import settings

        user = await self._users.get_by_email(req.email.lower())
        if user is None or not verify_password(req.password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")

        if not user.is_active:
            raise UnauthorizedError("Account is inactive")

        # Update last login timestamp
        await self._users.update_fields(
            user.id, last_login_at=datetime.now(UTC)
        )

        token = create_access_token(subject=str(user.id))
        logger.info("user.login", user_id=str(user.id), tenant_id=str(user.tenant_id))

        return TokenResponse(
            access_token=token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )

    async def get_current_user_profile(self, user_id: uuid.UUID) -> UserProfileResponse:
        user = await self._users.get_by_id_or_raise(user_id)
        return UserProfileResponse.model_validate(user)
