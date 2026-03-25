"""Schemas for /api/v1/reports endpoints."""

from app.schemas.common import BaseSchema


class AccountSummary(BaseSchema):
    account_id: str
    account_alias: str | None
    total_findings: int
    open_findings: int
    critical_findings: int


class ComplianceSummary(BaseSchema):
    framework_id: str
    total: int
    passing: int
    coverage_pct: float


class ExecutiveSummaryResponse(BaseSchema):
    generated_at: str
    workspace_id: str
    period_days: int  # 30

    # Finding totals
    total_findings: int
    open_findings: int
    critical_open: int
    high_open: int

    # Trend (last N days)
    new_last_7_days: int
    resolved_last_7_days: int

    # Risk
    avg_risk_score: float | None
    mttr_days: float | None  # mean time to resolve (days); None if no resolved findings

    # Top 10 riskiest open findings
    top_findings: list[dict]  # id, title, severity, risk_score, resource_type

    # Per-account breakdown
    accounts: list[AccountSummary]

    # Compliance coverage
    compliance: list[ComplianceSummary]
