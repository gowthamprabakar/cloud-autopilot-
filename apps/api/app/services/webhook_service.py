"""
WebhookService — business logic for webhook destination management and dispatch.
"""
import hashlib
import hmac
import json
import secrets
import uuid

import httpx
import structlog

from app.repositories.webhook_repository import WebhookRepository
from app.schemas.webhook import WebhookCreate, WebhookCreatedResponse, WebhookResponse

logger = structlog.get_logger(__name__)


class WebhookService:
    def __init__(self, repo: WebhookRepository) -> None:
        self.repo = repo

    async def create(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID | None,
        req: WebhookCreate,
    ) -> WebhookCreatedResponse:
        secret = secrets.token_hex(32)  # 64 hex chars
        events_json = json.dumps(req.events)
        record = await self.repo.create(
            workspace_id, user_id, req.name, req.url, secret, events_json
        )
        resp = WebhookCreatedResponse(
            id=record.id,
            workspace_id=record.workspace_id,
            name=record.name,
            url=record.url,
            events=json.loads(record.events) if isinstance(record.events, str) else record.events,
            is_active=record.is_active,
            created_at=record.created_at,
            updated_at=record.updated_at,
            secret=secret,
        )
        return resp

    async def list_webhooks(self, workspace_id: uuid.UUID) -> list[WebhookResponse]:
        records = await self.repo.list_by_workspace(workspace_id)
        result = []
        for r in records:
            w = WebhookResponse(
                id=r.id,
                workspace_id=r.workspace_id,
                name=r.name,
                url=r.url,
                events=json.loads(r.events) if isinstance(r.events, str) else r.events,
                is_active=r.is_active,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            result.append(w)
        return result

    async def delete(self, webhook_id: uuid.UUID, workspace_id: uuid.UUID) -> bool:
        return await self.repo.delete(webhook_id, workspace_id)

    async def dispatch(
        self, workspace_id: uuid.UUID, event_name: str, payload: dict
    ) -> None:
        """
        Fire-and-forget: send HMAC-signed POST to all active webhooks for this event.
        Never raises — errors are logged and swallowed.
        Signature: X-Copilot-Signature: sha256=<hmac_hex>
        """
        hooks = await self.repo.list_active_for_event(workspace_id, event_name)
        for hook in hooks:
            try:
                body = json.dumps({"event": event_name, "data": payload}, default=str)
                sig = "sha256=" + hmac.new(
                    hook.secret.encode(), body.encode(), digestmod=hashlib.sha256
                ).hexdigest()
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(
                        hook.url,
                        content=body,
                        headers={
                            "Content-Type": "application/json",
                            "X-Copilot-Signature": sig,
                            "X-Copilot-Event": event_name,
                        },
                    )
                logger.info("webhook.dispatched", hook_id=str(hook.id), event=event_name)
            except Exception as exc:
                logger.warning(
                    "webhook.dispatch_failed", hook_id=str(hook.id), error=str(exc)
                )
