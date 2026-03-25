"""
WorkspaceSettings Repository — data access for workspace_settings table.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace_settings import WorkspaceSettings


class WorkspaceSettingsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_or_create(self, workspace_id: uuid.UUID) -> WorkspaceSettings:
        """Return existing settings or create with defaults."""
        result = await self.db.execute(
            select(WorkspaceSettings).where(WorkspaceSettings.workspace_id == workspace_id)
        )
        settings = result.scalar_one_or_none()
        if settings is None:
            settings = WorkspaceSettings(workspace_id=workspace_id)
            self.db.add(settings)
            await self.db.flush()
            await self.db.refresh(settings)
        return settings

    async def update(self, workspace_id: uuid.UUID, **kwargs) -> WorkspaceSettings:
        """Update specific fields. Returns updated settings."""
        if 'jira_api_token' in kwargs and kwargs['jira_api_token']:
            from app.services.totp_service import encrypt_secret
            kwargs['jira_api_token'] = encrypt_secret(kwargs['jira_api_token'])
        settings = await self.get_or_create(workspace_id)
        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        self.db.add(settings)
        await self.db.flush()
        await self.db.refresh(settings)
        return settings

    async def get_jira_token_decrypted(self, workspace_id) -> str | None:
        """Return decrypted Jira API token for internal service use."""
        # Ensure UUID type for the query
        if isinstance(workspace_id, str):
            workspace_id = uuid.UUID(workspace_id)
        settings = await self.get_or_create(workspace_id)
        if not settings.jira_api_token:
            return None
        try:
            from app.services.totp_service import decrypt_secret
            return decrypt_secret(settings.jira_api_token)
        except Exception:
            # Token may be stored unencrypted (legacy) — return as-is
            return settings.jira_api_token
