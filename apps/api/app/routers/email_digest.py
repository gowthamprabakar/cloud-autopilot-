"""
Email digest router — manually trigger digest emails or test SMTP config.

POST /email/test            → send a test email to the current user (admin only)
POST /email/digest/weekly   → send weekly digest to all active users in workspace (admin only)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import CurrentUserDep, require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.services.email_service import EmailService

router = APIRouter(prefix="/email", tags=["email"])


@router.post("/test", status_code=202)
async def send_test_email(
    current_user: CurrentUserDep,
    _: User = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN),
):
    """Send a test email to the current user to verify SMTP config."""
    svc = EmailService()
    sent = await svc.send(
        current_user.email,
        "Test Email — Cloud Posture Copilot",
        "<h1>Test email working!</h1><p>SMTP is configured correctly.</p>",
        "Test email working! SMTP is configured correctly.",
    )
    return {"sent": sent, "to": current_user.email, "smtp_enabled": settings.email_enabled}


@router.post("/digest/weekly", status_code=202)
async def send_weekly_digest(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
    _: User = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN),
):
    """Trigger immediate weekly digest for the workspace."""
    from app.repositories.report_schedule_repository import ReportScheduleRepository
    from app.services.digest_service import DigestService
    import json

    repo = ReportScheduleRepository(db)
    schedule = await repo.get_or_create(str(current_user.workspace_id))
    recipients = []
    if schedule.recipients:
        try:
            recipients = json.loads(schedule.recipients)
        except Exception:
            recipients = []

    svc = DigestService(db)
    sent = await svc.send_digest(str(current_user.workspace_id), recipients)
    await repo.mark_sent(schedule.id)

    return {"sent": sent, "workspace_id": str(current_user.workspace_id), "recipients": recipients}


@router.get("/status")
async def get_email_status(current_user: CurrentUserDep):
    """Return SMTP configuration status."""
    return {
        "configured": settings.email_enabled,
        "host": settings.smtp_host if settings.smtp_host else None,
        "port": settings.smtp_port if settings.smtp_host else None,
        "from_email": settings.smtp_from_email if settings.smtp_host else None,
    }
