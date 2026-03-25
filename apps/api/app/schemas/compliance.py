"""
Compliance schemas — request/response contracts for /api/v1/compliance.
"""

from app.schemas.common import BaseSchema

# Canonical display names for known framework IDs
FRAMEWORK_DISPLAY_NAMES: dict[str, str] = {
    "CIS_AWS_1.4": "CIS AWS Foundations Benchmark v1.4",
    "PCI_DSS_3.2.1": "PCI DSS v3.2.1",
    "NIST_CSF": "NIST SP 800-53",
    "SOC2": "SOC 2 Type II",
}


class ComplianceFrameworkSummary(BaseSchema):
    """Summary for a single compliance framework."""
    framework_id: str
    display_name: str
    total_controls: int
    passing: int
    failing: int
    coverage_pct: float


class ComplianceStatsResponse(BaseSchema):
    """Top-level compliance overview response."""
    frameworks: list[ComplianceFrameworkSummary]
    last_updated: str | None
