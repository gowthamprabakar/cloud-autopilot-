# Import all models here — Alembic autogenerate requires every model
# to be imported before it can detect schema changes.
from app.models.enums import (
    AwsAccountStatus,
    FindingSeverity,
    FindingSource,
    FindingStatus,
    JobRunStatus,
    TenantPlan,
    TenantStatus,
    UserRole,
    WorkspaceStatus,
)
from app.models.tenant import Tenant
from app.models.user import User
from app.models.workspace import Workspace
from app.models.aws_account import AwsAccount
from app.models.job_run import JobRun
from app.models.source_finding import SourceFinding
from app.models.canonical_finding import CanonicalFinding
from app.models.audit_log import AuditLog
from app.models.notification import Notification
from app.models.suppression_rule import SuppressionRule
from app.models.revoked_token import RevokedToken
from app.models.refresh_token import RefreshToken
from app.models.api_key import ApiKey
from app.models.webhook_destination import WebhookDestination
from app.models.finding_comment import FindingComment
from app.models.finding_assignment import FindingAssignment
from app.models.workspace_settings import WorkspaceSettings
from app.models.jira_ticket import JiraTicket
from app.models.onboarding_progress import OnboardingProgress
from app.models.report_schedule import ReportSchedule
from app.models.security_graph_node import SecurityGraphNode
from app.models.security_graph_edge import SecurityGraphEdge
from app.models.attack_path import AttackPath
# Sprint 18 — THINK layer agent models
from app.models.scan_job import ScanJob
from app.models.agent_result import AgentResult
from app.models.agent_audit_log import AgentAuditLog
# Sprint 32 — Multi-tenant RBAC
from app.models.tenant_config import TenantConfig
# OmniSec swarm agent models
from app.models.simulation_run import SimulationRun
# Sprint 34 — Immutable audit trail
from app.models.simulation_audit import SimulationAuditEntry
from app.models.swarm_agent import SwarmAgent
from app.models.comm_message import CommMessage
from app.models.validation_gate import ValidationGate

__all__ = [
    "Tenant",
    "Workspace",
    "User",
    "AwsAccount",
    "JobRun",
    "SourceFinding",
    "CanonicalFinding",
    "AuditLog",
    "Notification",
    "SuppressionRule",
    "RevokedToken",
    "RefreshToken",
    "ApiKey",
    "WebhookDestination",
    "FindingComment",
    "FindingAssignment",
    "WorkspaceSettings",
    "JiraTicket",
    "OnboardingProgress",
    "ReportSchedule",
    "SecurityGraphNode",
    "SecurityGraphEdge",
    "AttackPath",
    "ScanJob",
    "AgentResult",
    "AgentAuditLog",
    "SimulationRun",
    "SwarmAgent",
    "CommMessage",
    "ValidationGate",
    "SimulationAuditEntry",
    "TenantConfig",
    "UserRole",
    "TenantPlan",
    "TenantStatus",
    "WorkspaceStatus",
    "AwsAccountStatus",
    "FindingSeverity",
    "FindingSource",
    "FindingStatus",
    "JobRunStatus",
]
