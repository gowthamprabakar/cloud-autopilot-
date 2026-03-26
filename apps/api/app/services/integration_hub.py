"""
IntegrationHub — External service connector manager.

Sprint 32: Manages integrations with:
1. Slack      — Post simulation results, gate failures, critical alerts
2. Jira       — Auto-create tickets for failed gates, critical findings
3. PagerDuty  — Trigger incidents for critical simulation failures
4. SIEM       — Forward events in CEF/LEEF/JSON format
5. GitHub     — Create PRs with IaC remediation code
6. GitLab     — Create MRs with IaC remediation code
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import Integration

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

VALID_TYPES = {"slack", "jira", "pagerduty", "siem", "github", "gitlab"}

_SEVERITY_EMOJI = {
    "critical": "\U0001f534",  # red circle
    "high": "\U0001f7e0",      # orange circle
    "medium": "\U0001f7e1",    # yellow circle
    "low": "\U0001f7e2",       # green circle
    "info": "\U0001f535",      # blue circle
}

_PAGERDUTY_SEVERITY_MAP = {
    "critical": "critical",
    "high": "error",
    "medium": "warning",
    "low": "info",
    "info": "info",
}

_HTTP_TIMEOUT = 15.0  # seconds


# ── Helpers ──────────────────────────────────────────────────────────────────


def _parse_config(config_json: str | None) -> dict[str, Any]:
    """Safely parse the encrypted JSON config blob."""
    if not config_json:
        return {}
    try:
        return json.loads(config_json)
    except (json.JSONDecodeError, TypeError):
        return {}


def _matches_filter(event_filter_json: str | None, event_type: str) -> bool:
    """Return True if the event_type is accepted by the integration filter."""
    if not event_filter_json:
        return True  # no filter = accept everything
    try:
        allowed = json.loads(event_filter_json)
        if not isinstance(allowed, list):
            return True
        return event_type in allowed
    except (json.JSONDecodeError, TypeError):
        return True


def _cef_format(event_type: str, payload: dict[str, Any]) -> str:
    """Format event as ArcSight CEF string."""
    severity = payload.get("severity", "5")
    name = payload.get("title", event_type)
    desc = payload.get("description", "")[:1024]
    return (
        f"CEF:0|OmniSec|CloudCopilot|1.0|{event_type}|{name}|{severity}|"
        f"msg={desc}"
    )


def _leef_format(event_type: str, payload: dict[str, Any]) -> str:
    """Format event as IBM QRadar LEEF string."""
    severity = payload.get("severity", "5")
    name = payload.get("title", event_type)
    desc = payload.get("description", "")[:1024]
    return (
        f"LEEF:2.0|OmniSec|CloudCopilot|1.0|{event_type}|"
        f"cat={name}\tsev={severity}\tmsg={desc}"
    )


# ── Service ──────────────────────────────────────────────────────────────────


class IntegrationHub:
    """Manages CRUD and event dispatch for external integrations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── CRUD ──────────────────────────────────────────────────────────────

    async def list_integrations(self, workspace_id: uuid.UUID) -> list[Integration]:
        """Return all integrations for a workspace."""
        result = await self.db.execute(
            select(Integration)
            .where(Integration.workspace_id == workspace_id)
            .order_by(Integration.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_integration(
        self,
        workspace_id: uuid.UUID,
        integration_type: str,
        name: str,
        config: dict[str, Any],
        event_filter: list[str] | None = None,
    ) -> Integration:
        """Persist a new integration record."""
        if integration_type not in VALID_TYPES:
            raise ValueError(
                f"Invalid integration_type '{integration_type}'. "
                f"Must be one of: {', '.join(sorted(VALID_TYPES))}"
            )
        integration = Integration(
            workspace_id=workspace_id,
            integration_type=integration_type,
            name=name,
            config_json=json.dumps(config),
            event_filter=json.dumps(event_filter) if event_filter else None,
        )
        self.db.add(integration)
        await self.db.commit()
        await self.db.refresh(integration)
        return integration

    async def update_integration(
        self, integration_id: uuid.UUID, updates: dict[str, Any]
    ) -> Integration | None:
        """Patch-update an existing integration."""
        result = await self.db.execute(
            select(Integration).where(Integration.id == integration_id)
        )
        integration = result.scalar_one_or_none()
        if not integration:
            return None

        for field in ("name", "is_enabled", "event_filter"):
            if field in updates:
                value = updates[field]
                if field == "event_filter" and isinstance(value, list):
                    value = json.dumps(value)
                setattr(integration, field, value)

        if "config" in updates and isinstance(updates["config"], dict):
            integration.config_json = json.dumps(updates["config"])

        integration.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(integration)
        return integration

    async def delete_integration(self, integration_id: uuid.UUID) -> bool:
        """Remove an integration. Returns True if a row was deleted."""
        result = await self.db.execute(
            delete(Integration).where(Integration.id == integration_id)
        )
        await self.db.commit()
        return result.rowcount > 0  # type: ignore[union-attr]

    async def test_integration(self, integration_id: uuid.UUID) -> dict[str, Any]:
        """Send a test payload to verify connectivity."""
        result = await self.db.execute(
            select(Integration).where(Integration.id == integration_id)
        )
        integration = result.scalar_one_or_none()
        if not integration:
            return {"ok": False, "error": "Integration not found"}

        config = _parse_config(integration.config_json)
        test_payload = {
            "title": "OmniSec Connectivity Test",
            "description": "This is a test event from OmniSec Integration Hub.",
            "severity": "info",
            "timestamp": datetime.now(UTC).isoformat(),
        }

        dispatch_fn = self._dispatch_map().get(integration.integration_type)
        if not dispatch_fn:
            return {"ok": False, "error": f"Unknown type: {integration.integration_type}"}

        try:
            resp = await dispatch_fn(config, "integration.test", test_payload)
            # Record success
            integration.last_sync_at = datetime.now(UTC)
            integration.last_error = None
            await self.db.commit()
            return {"ok": True, **resp}
        except Exception as exc:
            integration.last_error = str(exc)[:2048]
            await self.db.commit()
            return {"ok": False, "error": str(exc)}

    # ── Dispatch ──────────────────────────────────────────────────────────

    def _dispatch_map(self) -> dict[str, Any]:
        return {
            "slack": self._send_slack,
            "jira": self._create_jira_ticket,
            "pagerduty": self._trigger_pagerduty,
            "siem": self._forward_to_siem,
            "github": self._create_github_pr,
            "gitlab": self._create_gitlab_mr,
        }

    async def dispatch_event(
        self,
        workspace_id: uuid.UUID,
        event_type: str,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Send event to all enabled integrations matching the event filter."""
        result = await self.db.execute(
            select(Integration).where(
                Integration.workspace_id == workspace_id,
                Integration.is_enabled.is_(True),
            )
        )
        integrations = list(result.scalars().all())
        results: list[dict[str, Any]] = []

        for integration in integrations:
            if not _matches_filter(integration.event_filter, event_type):
                continue

            config = _parse_config(integration.config_json)
            dispatch_fn = self._dispatch_map().get(integration.integration_type)
            if not dispatch_fn:
                results.append({
                    "integration_id": str(integration.id),
                    "type": integration.integration_type,
                    "ok": False,
                    "error": "Unknown integration type",
                })
                continue

            try:
                resp = await dispatch_fn(config, event_type, payload)
                integration.last_sync_at = datetime.now(UTC)
                integration.last_error = None
                results.append({
                    "integration_id": str(integration.id),
                    "type": integration.integration_type,
                    "ok": True,
                    **resp,
                })
            except Exception as exc:
                error_msg = str(exc)[:2048]
                integration.last_error = error_msg
                logger.warning(
                    "integration dispatch failed id=%s type=%s error=%s",
                    integration.id,
                    integration.integration_type,
                    error_msg,
                )
                results.append({
                    "integration_id": str(integration.id),
                    "type": integration.integration_type,
                    "ok": False,
                    "error": error_msg,
                })

        await self.db.commit()
        return results

    # ── Slack ─────────────────────────────────────────────────────────────

    async def _send_slack(
        self, config: dict[str, Any], event_type: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Post to Slack webhook with formatted rich blocks."""
        webhook_url = config.get("webhook_url")
        if not webhook_url:
            raise ValueError("Slack webhook_url is required")

        severity = payload.get("severity", "info")
        emoji = _SEVERITY_EMOJI.get(severity, "\u2139\ufe0f")
        title = payload.get("title", event_type)
        description = payload.get("description", "No details provided.")
        timestamp = payload.get("timestamp", datetime.now(UTC).isoformat())

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{emoji} {title}"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Event:*\n`{event_type}`"},
                    {"type": "mrkdwn", "text": f"*Severity:*\n{severity.upper()}"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": description[:2900],
                },
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"OmniSec Integration Hub | {timestamp}"},
                ],
            },
        ]

        slack_payload: dict[str, Any] = {"blocks": blocks}
        channel = config.get("channel")
        if channel:
            slack_payload["channel"] = channel

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.post(webhook_url, json=slack_payload)
            resp.raise_for_status()

        return {"status_code": resp.status_code, "channel": channel}

    # ── Jira ──────────────────────────────────────────────────────────────

    async def _create_jira_ticket(
        self, config: dict[str, Any], event_type: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a Jira issue for gate failures or critical findings."""
        base_url = config.get("base_url", "").rstrip("/")
        email = config.get("email")
        api_token = config.get("api_token")
        project_key = config.get("project_key")

        if not all([base_url, email, api_token, project_key]):
            raise ValueError(
                "Jira requires base_url, email, api_token, and project_key"
            )

        severity = payload.get("severity", "medium")
        priority_map = {
            "critical": "Highest",
            "high": "High",
            "medium": "Medium",
            "low": "Low",
            "info": "Lowest",
        }

        title = payload.get("title", f"OmniSec: {event_type}")
        description = payload.get("description", "No details provided.")
        labels = payload.get("labels", ["omnisec", "auto-created"])

        issue_data = {
            "fields": {
                "project": {"key": project_key},
                "summary": title[:255],
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {"type": "text", "text": description[:32000]}
                            ],
                        }
                    ],
                },
                "issuetype": {"name": "Bug"},
                "priority": {"name": priority_map.get(severity, "Medium")},
                "labels": labels,
            }
        }

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/rest/api/3/issue",
                json=issue_data,
                auth=(email, api_token),
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "issue_key": data.get("key"),
            "issue_id": data.get("id"),
            "self_url": data.get("self"),
        }

    # ── PagerDuty ─────────────────────────────────────────────────────────

    async def _trigger_pagerduty(
        self, config: dict[str, Any], event_type: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Trigger a PagerDuty incident via Events API v2."""
        routing_key = config.get("api_key")
        if not routing_key:
            raise ValueError("PagerDuty api_key (routing key) is required")

        severity = payload.get("severity", "warning")
        pd_severity = _PAGERDUTY_SEVERITY_MAP.get(severity, "warning")
        title = payload.get("title", f"OmniSec: {event_type}")
        description = payload.get("description", "")

        event_payload = {
            "routing_key": routing_key,
            "event_action": "trigger",
            "payload": {
                "summary": title[:1024],
                "severity": pd_severity,
                "source": "omnisec-integration-hub",
                "component": event_type,
                "custom_details": {
                    "description": description[:4000],
                    "event_type": event_type,
                    "timestamp": payload.get(
                        "timestamp", datetime.now(UTC).isoformat()
                    ),
                },
            },
        }

        service_id = config.get("service_id")
        if service_id:
            event_payload["payload"]["group"] = service_id  # type: ignore[index]

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=event_payload,
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "status": data.get("status"),
            "dedup_key": data.get("dedup_key"),
            "message": data.get("message"),
        }

    # ── SIEM ──────────────────────────────────────────────────────────────

    async def _forward_to_siem(
        self, config: dict[str, Any], event_type: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Forward event to SIEM endpoint in CEF, LEEF, or JSON format."""
        endpoint_url = config.get("endpoint_url")
        if not endpoint_url:
            raise ValueError("SIEM endpoint_url is required")

        fmt = config.get("format", "json").lower()
        api_key = config.get("api_key")

        headers: dict[str, str] = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        if fmt == "cef":
            body = _cef_format(event_type, payload)
            headers["Content-Type"] = "text/plain"
        elif fmt == "leef":
            body = _leef_format(event_type, payload)
            headers["Content-Type"] = "text/plain"
        else:
            body = json.dumps(
                {
                    "event_type": event_type,
                    "source": "omnisec",
                    "timestamp": payload.get(
                        "timestamp", datetime.now(UTC).isoformat()
                    ),
                    **payload,
                }
            )
            headers["Content-Type"] = "application/json"

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.post(endpoint_url, content=body, headers=headers)
            resp.raise_for_status()

        return {"status_code": resp.status_code, "format": fmt}

    # ── GitHub ────────────────────────────────────────────────────────────

    async def _create_github_pr(
        self, config: dict[str, Any], event_type: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a GitHub PR with IaC remediation from DEFEND-01 output."""
        token = config.get("token")
        org = config.get("org")
        repo = config.get("repo")
        if not all([token, org, repo]):
            raise ValueError("GitHub requires token, org, and repo")

        base_branch = config.get("base_branch", "main")
        title = payload.get("title", f"OmniSec remediation: {event_type}")
        description = payload.get("description", "Auto-generated by OmniSec.")
        file_path = payload.get("file_path", "remediation/fix.tf")
        file_content = payload.get("file_content", "# No remediation content")
        branch_name = f"omnisec/remediation-{uuid.uuid4().hex[:8]}"

        gh_headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        api_base = f"https://api.github.com/repos/{org}/{repo}"

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            # 1. Get base branch SHA
            ref_resp = await client.get(
                f"{api_base}/git/ref/heads/{base_branch}",
                headers=gh_headers,
            )
            ref_resp.raise_for_status()
            base_sha = ref_resp.json()["object"]["sha"]

            # 2. Create new branch
            await client.post(
                f"{api_base}/git/refs",
                headers=gh_headers,
                json={"ref": f"refs/heads/{branch_name}", "sha": base_sha},
            )

            # 3. Create/update file on new branch
            import base64

            encoded = base64.b64encode(file_content.encode()).decode()
            await client.put(
                f"{api_base}/contents/{file_path}",
                headers=gh_headers,
                json={
                    "message": f"fix: {title}",
                    "content": encoded,
                    "branch": branch_name,
                },
            )

            # 4. Open PR
            pr_resp = await client.post(
                f"{api_base}/pulls",
                headers=gh_headers,
                json={
                    "title": title[:255],
                    "body": description[:65000],
                    "head": branch_name,
                    "base": base_branch,
                },
            )
            pr_resp.raise_for_status()
            pr_data = pr_resp.json()

        return {
            "pr_number": pr_data.get("number"),
            "pr_url": pr_data.get("html_url"),
            "branch": branch_name,
        }

    # ── GitLab ────────────────────────────────────────────────────────────

    async def _create_gitlab_mr(
        self, config: dict[str, Any], event_type: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a GitLab MR with IaC remediation code."""
        token = config.get("token")
        project_id = config.get("project_id")
        if not all([token, project_id]):
            raise ValueError("GitLab requires token and project_id")

        base_url = config.get("base_url", "https://gitlab.com")
        base_branch = config.get("base_branch", "main")
        title = payload.get("title", f"OmniSec remediation: {event_type}")
        description = payload.get("description", "Auto-generated by OmniSec.")
        file_path = payload.get("file_path", "remediation/fix.tf")
        file_content = payload.get("file_content", "# No remediation content")
        branch_name = f"omnisec/remediation-{uuid.uuid4().hex[:8]}"

        gl_headers = {
            "PRIVATE-TOKEN": token,
            "Content-Type": "application/json",
        }
        api_base = f"{base_url.rstrip('/')}/api/v4/projects/{project_id}"

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            # 1. Create branch
            await client.post(
                f"{api_base}/repository/branches",
                headers=gl_headers,
                json={"branch": branch_name, "ref": base_branch},
            )

            # 2. Create/update file
            import base64

            encoded = base64.b64encode(file_content.encode()).decode()
            await client.post(
                f"{api_base}/repository/files/{file_path.replace('/', '%2F')}",
                headers=gl_headers,
                json={
                    "branch": branch_name,
                    "content": encoded,
                    "encoding": "base64",
                    "commit_message": f"fix: {title}",
                },
            )

            # 3. Open MR
            mr_resp = await client.post(
                f"{api_base}/merge_requests",
                headers=gl_headers,
                json={
                    "source_branch": branch_name,
                    "target_branch": base_branch,
                    "title": title[:255],
                    "description": description[:65000],
                },
            )
            mr_resp.raise_for_status()
            mr_data = mr_resp.json()

        return {
            "mr_iid": mr_data.get("iid"),
            "mr_url": mr_data.get("web_url"),
            "branch": branch_name,
        }
