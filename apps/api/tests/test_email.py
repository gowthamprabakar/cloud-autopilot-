"""
Sprint 13 — Email Service tests.

SMTP is disabled by default in tests (smtp_host = ""), so most tests verify
the disabled-path behaviour without any mocking. Two tests patch settings to
verify the enabled path.
"""

import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient

# ── Shared registration payload (mirrors test_auth.py) ───────────────────────

REGISTER_PAYLOAD = {
    "tenant_name": "Email Test Corp",
    "tenant_slug": "email-test-corp",
    "workspace_name": "Production",
    "email": "admin@emailtest.com",
    "password": "supersecret99",
    "full_name": "Admin User",
    "plan": "baseline",
}


@pytest.fixture
async def _register(client: AsyncClient):
    """Register a fresh admin user and return token + user_id."""
    res = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert res.status_code == 201, res.text
    data = res.json()
    return {"token": data["access_token"], "user_id": data["user_id"]}


# ── Unit tests ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_email_service_skipped_when_smtp_not_configured(client: AsyncClient):
    """EmailService.send returns False when smtp_host is blank (default in tests)."""
    from app.services.email_service import EmailService
    svc = EmailService()
    result = await svc.send("test@example.com", "Test", "<p>hello</p>")
    assert result is False  # smtp_host is "" in test config


@pytest.mark.asyncio
async def test_email_service_sends_when_smtp_configured():
    """EmailService._send_sync is called when smtp_host is set."""
    from app.services.email_service import EmailService
    with patch.object(EmailService, "_send_sync") as mock_send:
        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.email_enabled = True
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.smtp_from_email = "noreply@example.com"
            mock_settings.smtp_from_name = "Test"
            mock_settings.smtp_use_tls = True
            svc = EmailService()
            result = await svc.send("to@example.com", "Subj", "<p>hi</p>")
            mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_email_service_swallows_smtp_errors():
    """EmailService.send returns False on SMTP error — never raises."""
    from app.services.email_service import EmailService
    with patch.object(EmailService, "_send_sync", side_effect=Exception("SMTP error")):
        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.email_enabled = True
            svc = EmailService()
            result = await svc.send("to@example.com", "Subj", "<p>hi</p>")
            assert result is False


@pytest.mark.asyncio
async def test_assignment_email_template_structure():
    """finding_assigned_email returns valid (subject, html, text) tuple."""
    from app.services.email_templates import finding_assigned_email
    subj, html, text = finding_assigned_email(
        assignee_name="Alice",
        finding_title="S3 bucket public",
        finding_severity="high",
        assigned_by="Bob",
        due_date="March 20, 2026",
        note="urgent",
        finding_url="/dashboard/findings/123",
    )
    assert "S3 bucket public" in subj
    assert "Alice" in html
    assert "high" in html.lower()
    assert "urgent" in html


@pytest.mark.asyncio
async def test_sla_breach_template_structure():
    """sla_breach_email returns correct subject and HTML content."""
    from app.services.email_templates import sla_breach_email
    findings = [{"title": "Bad bucket", "severity": "critical", "days_overdue": 5, "url": "/f/1"}]
    subj, html, text = sla_breach_email("Admin", findings, "Acme")
    assert "1 finding" in subj
    assert "Bad bucket" in html
    assert "5 days overdue" in html


@pytest.mark.asyncio
async def test_user_invited_template_structure():
    """user_invited_email returns correct subject and HTML content."""
    from app.services.email_templates import user_invited_email
    subj, html, text = user_invited_email("Alice", "Bob", "Acme WS", "/login", "tmp-pass-123")
    assert "Acme WS" in subj
    assert "tmp-pass-123" in html
    assert "/login" in html


# ── Endpoint tests ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_email_test_endpoint_returns_sent_false_no_smtp(client: AsyncClient, _register):
    """POST /email/test returns {sent: false} when SMTP not configured (test env)."""
    token = _register["token"]
    res = await client.post(
        "/api/v1/email/test",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 202
    assert res.json()["sent"] is False
    assert res.json()["smtp_enabled"] is False


@pytest.mark.asyncio
async def test_weekly_digest_endpoint_returns_202(client: AsyncClient, _register):
    """POST /email/digest/weekly returns 202 for admin."""
    token = _register["token"]
    res = await client.post(
        "/api/v1/email/digest/weekly",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 202
