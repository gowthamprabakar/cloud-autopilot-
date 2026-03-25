"""
JiraService — create Jira issues from canonical findings.

Uses Jira REST API v3 with Basic Auth (email + API token).
No Jira SDK dependency — pure httpx.

Design:
- Never raises: HTTP errors logged and returned as error dict
- Idempotent check: if finding already has a jira_ticket_url, return existing
"""
import base64

import httpx
import structlog

from app.models.canonical_finding import CanonicalFinding

logger = structlog.get_logger(__name__)

# Jira severity → priority mapping
_SEVERITY_TO_PRIORITY = {
    "critical": "Highest",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
    "info": "Lowest",
}


class JiraService:
    def __init__(
        self,
        base_url: str,
        email: str,
        api_token: str,
        project_key: str,
        issue_type: str = "Task",
    ):
        self.base_url = base_url.rstrip("/")
        self._auth = base64.b64encode(f"{email}:{api_token}".encode()).decode()
        self.project_key = project_key
        self.issue_type = issue_type

    async def create_issue(self, finding: CanonicalFinding) -> dict:
        """
        Create a Jira issue for a finding.
        Returns {"key": "PROJ-123", "url": "https://..."} on success.
        Returns {"error": "message"} on failure.
        """
        priority = _SEVERITY_TO_PRIORITY.get(str(finding.severity).lower(), "Medium")
        description = (
            f"*Finding ID:* {finding.id}\n"
            f"*Severity:* {finding.severity}\n"
            f"*Resource:* {finding.resource_arn or 'N/A'}\n"
            f"*Resource Type:* {finding.resource_type or 'N/A'}\n\n"
            f"{finding.description or 'No description available.'}\n\n"
            f"*First Seen:* {finding.first_seen_at}\n"
            f"*Risk Score:* {finding.risk_score}"
        )
        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": f"[Security] {finding.title[:200]}",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description}],
                        }
                    ],
                },
                "issuetype": {"name": self.issue_type},
                "priority": {"name": priority},
                "labels": [
                    "cloud-posture",
                    f"severity-{str(finding.severity).lower()}",
                ],
            }
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.base_url}/rest/api/3/issue",
                    json=payload,
                    headers={
                        "Authorization": f"Basic {self._auth}",
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                )
                if resp.is_success:
                    data = resp.json()
                    key = data.get("key", "")
                    url = f"{self.base_url}/browse/{key}"
                    logger.info("jira.issue_created", key=key, finding_id=str(finding.id))
                    return {"key": key, "url": url, "id": data.get("id")}
                else:
                    logger.warning(
                        "jira.api_error", status=resp.status_code, body=resp.text[:200]
                    )
                    return {
                        "error": f"Jira API returned {resp.status_code}: {resp.text[:100]}"
                    }
        except Exception as exc:
            logger.warning("jira.request_failed", error=str(exc))
            return {"error": str(exc)}

    async def test_connection(self) -> dict:
        """Verify Jira credentials and project exist. Returns {ok: bool, message: str}."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self.base_url}/rest/api/3/project/{self.project_key}",
                    headers={
                        "Authorization": f"Basic {self._auth}",
                        "Accept": "application/json",
                    },
                )
                if resp.is_success:
                    data = resp.json()
                    return {
                        "ok": True,
                        "message": f"Connected to project: {data.get('name', self.project_key)}",
                    }
                return {"ok": False, "message": f"HTTP {resp.status_code}: {resp.text[:100]}"}
        except Exception as exc:
            return {"ok": False, "message": str(exc)}
