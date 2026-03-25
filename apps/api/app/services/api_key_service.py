"""
ApiKeyService — business logic for workspace API key management.
"""

import hashlib
import secrets
import uuid

from app.repositories.api_key_repository import ApiKeyRepository
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreatedResponse, ApiKeyResponse


def _generate_key() -> tuple[str, str, str]:
    """Returns (raw_key, key_prefix, key_hash).

    Generates: 'sk-' + 48 url-safe base64 chars (~51 chars total).
    """
    raw = "sk-" + secrets.token_urlsafe(36)  # 36 bytes → 48 url-safe chars
    key_prefix = raw[:10]  # show "sk-XXXXXXX" in UI
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, key_prefix, key_hash


class ApiKeyService:
    def __init__(self, repo: ApiKeyRepository) -> None:
        self.repo = repo

    async def create_key(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID | None,
        req: ApiKeyCreate,
    ) -> ApiKeyCreatedResponse:
        """Generate a new API key and store only its hash."""
        raw, prefix, key_hash = _generate_key()
        record = await self.repo.create(
            workspace_id=workspace_id,
            created_by_user_id=user_id,
            name=req.name,
            key_prefix=prefix,
            key_hash=key_hash,
            expires_at=req.expires_at,
        )
        response = ApiKeyResponse.model_validate(record)
        return ApiKeyCreatedResponse(**response.model_dump(), raw_key=raw)

    async def list_keys(self, workspace_id: uuid.UUID) -> list[ApiKeyResponse]:
        """Return all keys for the workspace (no hashes, no raw keys)."""
        keys = await self.repo.list_by_workspace(workspace_id)
        return [ApiKeyResponse.model_validate(k) for k in keys]

    async def revoke_key(
        self, key_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> bool:
        """Soft-delete: set is_active=False. Returns False if not found."""
        return await self.repo.revoke(key_id, workspace_id)
