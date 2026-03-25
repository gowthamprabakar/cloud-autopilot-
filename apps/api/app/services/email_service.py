"""
EmailService — async SMTP email delivery via stdlib smtplib (run in threadpool).

Design:
- Never raises — all errors are logged and swallowed so email failures
  never block the primary operation (assignment, SLA check, etc.)
- email_enabled guard: if smtp_host is blank, logs a debug message and returns
- HTML + plain-text multipart messages
- Simple Python f-string templates (no external template engine)
"""
import asyncio
import email.mime.multipart
import email.mime.text
import smtplib
import ssl

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class EmailService:
    """Thin async wrapper around smtplib (sync, run in threadpool)."""

    async def send(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
    ) -> bool:
        """
        Send an email. Returns True on success, False on failure.
        Never raises.
        """
        if not settings.email_enabled:
            logger.debug("email.skipped_no_smtp", to=to_email, subject=subject)
            return False

        try:
            await asyncio.get_event_loop().run_in_executor(
                None, self._send_sync, to_email, subject, html_body, text_body
            )
            logger.info("email.sent", to=to_email, subject=subject)
            return True
        except Exception as exc:
            logger.warning("email.failed", to=to_email, subject=subject, error=str(exc))
            return False

    def _send_sync(self, to_email: str, subject: str, html_body: str, text_body: str | None) -> None:
        msg = email.mime.multipart.MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        msg["To"] = to_email

        if text_body:
            msg.attach(email.mime.text.MIMEText(text_body, "plain"))
        msg.attach(email.mime.text.MIMEText(html_body, "html"))

        context = ssl.create_default_context()
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            if settings.smtp_use_tls:
                server.starttls(context=context)
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.smtp_from_email, to_email, msg.as_string())
