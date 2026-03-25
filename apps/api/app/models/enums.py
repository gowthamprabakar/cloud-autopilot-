"""
Domain enums — locked per SSOT.

Rules:
- Never duplicate or invent inconsistent enum values.
- Backend is the single source of truth for all enum values.
- Frontend mirrors these via lib/types.ts.
"""

from enum import StrEnum


class UserRole(StrEnum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"
    MSP_PARTNER = "msp_partner"


class TenantPlan(StrEnum):
    BASELINE = "baseline"
    OPS_MVP = "ops_mvp"
    MSP_VCISO = "msp_vciso"


class TenantStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"


class WorkspaceStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class AwsAccountStatus(StrEnum):
    PENDING = "pending"
    VALIDATING = "validating"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


class FindingSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ACCEPTED = "accepted"
    SUPPRESSED = "suppressed"


class JobRunStatus(StrEnum):
    """Persistent job execution status — mirrors BaseJob lifecycle."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FindingSource(StrEnum):
    """AWS service that produced the raw finding."""
    SECURITY_HUB = "security_hub"
    GUARD_DUTY = "guard_duty"
    INSPECTOR = "inspector"
    CONFIG = "config"
    IAM_ACCESS_ANALYZER = "iam_access_analyzer"
