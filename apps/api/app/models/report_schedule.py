"""Report schedule model for automated digest emails."""
import uuid
from datetime import datetime, UTC
from typing import Optional
from sqlalchemy import String, Boolean, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class ReportSchedule(Base):
    __tablename__ = "report_schedules"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    frequency: Mapped[str] = mapped_column(String(20), default="weekly")  # weekly | monthly
    day_of_week: Mapped[int] = mapped_column(Integer, default=1)  # 1=Monday ... 7=Sunday
    recipients: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of emails
    last_sent_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
