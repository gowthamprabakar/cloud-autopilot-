"""
Findings router — workspace-scoped canonical findings API.

All endpoints require authentication. workspace_id is scoped to
current_user.workspace_id.
"""

import csv
import io
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.enums import FindingSeverity, FindingStatus
from app.repositories.canonical_finding_repository import CanonicalFindingRepository
from app.repositories.finding_assignment_repository import FindingAssignmentRepository
from app.repositories.finding_comment_repository import FindingCommentRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.source_finding_repository import SourceFindingRepository
from app.repositories.user_repository import UserRepository
from app.schemas.assignment import AssignFindingRequest, AssignmentResponse
from app.schemas.finding import (
    BulkFindingUpdateRequest,
    BulkFindingUpdateResponse,
    CanonicalFindingResponse,
    FindingListResponse,
    FindingStatsResponse,
    FindingUpdateRequest,
    SeverityBreakdownItem,
)
from app.schemas.finding_comment import FindingCommentCreate, FindingCommentResponse
from app.services.assignment_service import AssignmentService
from app.services.email_service import EmailService
from app.services.finding_comment_service import FindingCommentService
from app.services.findings_service import FindingsService

router = APIRouter(prefix="/findings", tags=["findings"])


def _svc(db: AsyncSession = Depends(get_db)) -> FindingsService:
    return FindingsService(
        canonical_repo=CanonicalFindingRepository(db),
        source_repo=SourceFindingRepository(db),
    )


def _comment_svc(db: AsyncSession = Depends(get_db)) -> FindingCommentService:
    return FindingCommentService(
        comment_repo=FindingCommentRepository(db),
        canonical_repo=CanonicalFindingRepository(db),
        user_repo=UserRepository(db),
    )


def _assignment_svc(db: AsyncSession = Depends(get_db)) -> AssignmentService:
    return AssignmentService(
        assignment_repo=FindingAssignmentRepository(db),
        canonical_repo=CanonicalFindingRepository(db),
        user_repo=UserRepository(db),
        notification_repo=NotificationRepository(db),
        email_service=EmailService(),
    )


def _resolve_workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    return current_user.workspace_id


@router.get("", response_model=FindingListResponse)
async def list_findings(
    current_user: CurrentUserDep,
    svc: FindingsService = Depends(_svc),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    severity: FindingSeverity | None = Query(default=None),
    status: FindingStatus | None = Query(default=None),
    aws_account_id: uuid.UUID | None = Query(default=None),
    source: str | None = Query(default=None),
) -> FindingListResponse:
    workspace_id = _resolve_workspace_id(current_user)
    items, total = await svc.list_findings(
        workspace_id=workspace_id,
        severity=severity,
        status=status,
        aws_account_id=aws_account_id,
        source=source,
        page=page,
        page_size=page_size,
    )
    pages = max(1, (total + page_size - 1) // page_size)
    return FindingListResponse(
        items=[CanonicalFindingResponse.model_validate(f) for f in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/stats", response_model=FindingStatsResponse)
async def get_finding_stats(
    current_user: CurrentUserDep,
    svc: FindingsService = Depends(_svc),
) -> FindingStatsResponse:
    workspace_id = _resolve_workspace_id(current_user)
    stats = await svc.get_stats(workspace_id)
    by_severity: dict[str, int] = stats["by_severity"]
    breakdown = [
        SeverityBreakdownItem(
            severity=sev,
            count=cnt,
            risk_label=_risk_label(sev),
        )
        for sev, cnt in by_severity.items()
    ]
    return FindingStatsResponse(
        by_severity=by_severity,
        by_status=stats["by_status"],
        total=stats["total"],
        breakdown=breakdown,
    )


@router.get("/export")
async def export_findings_csv(
    current_user: CurrentUserDep,
    svc: FindingsService = Depends(_svc),
    severity: FindingSeverity | None = Query(default=None),
    status: FindingStatus | None = Query(default=None),
    aws_account_id: uuid.UUID | None = Query(default=None),
    source: str | None = Query(default=None),
) -> StreamingResponse:
    """
    Export all matching findings as CSV.
    Max 5000 findings. Same filters as GET /findings.
    Returns: text/csv with Content-Disposition: attachment
    """
    workspace_id = _resolve_workspace_id(current_user)
    # Fetch up to 5000 findings (no pagination for export)
    items, _ = await svc.list_findings(
        workspace_id=workspace_id,
        severity=severity,
        status=status,
        aws_account_id=aws_account_id,
        source=source,
        page=1,
        page_size=5000,
    )

    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        "id", "title", "severity", "status", "risk_score",
        "primary_source", "resource_type", "resource_arn", "region",
        "compliance_frameworks", "first_seen_at", "last_seen_at", "resolved_at",
        "aws_account_id",
    ])

    # Data rows
    for f in items:
        writer.writerow([
            str(f.id),
            f.title,
            f.severity,
            f.status,
            f.risk_score,
            f.primary_source,
            f.resource_type or "",
            f.resource_arn or "",
            f.region or "",
            "|".join(f.compliance_frameworks or []),
            f.first_seen_at or "",
            f.last_seen_at or "",
            f.resolved_at or "",
            str(f.aws_account_id),
        ])

    output.seek(0)
    today = date.today().isoformat()
    filename = f"findings-export-{today}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/bulk", response_model=BulkFindingUpdateResponse)
async def bulk_update_findings(
    req: BulkFindingUpdateRequest,
    current_user: CurrentUserDep,
    svc: FindingsService = Depends(_svc),
) -> BulkFindingUpdateResponse:
    """Bulk update status for up to 100 findings at once."""
    workspace_id = _resolve_workspace_id(current_user)
    updated, failed, errors = await svc.bulk_update_status(
        finding_ids=req.finding_ids,
        workspace_id=workspace_id,
        new_status=req.status,
    )
    return BulkFindingUpdateResponse(updated=updated, failed=failed, errors=errors)


# ── Assignment sub-routes (must be before /{finding_id}) ─────────────────────

@router.get("/assigned-to-me", response_model=list[AssignmentResponse])
async def list_my_assignments(
    current_user: CurrentUserDep,
    svc: AssignmentService = Depends(_assignment_svc),
) -> list[AssignmentResponse]:
    """List all active findings assigned to the current user."""
    workspace_id = _resolve_workspace_id(current_user)
    return await svc.list_my_assignments(current_user.id, workspace_id)


@router.post(
    "/{finding_id}/assign",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_finding(
    finding_id: uuid.UUID,
    req: AssignFindingRequest,
    current_user: CurrentUserDep,
    svc: AssignmentService = Depends(_assignment_svc),
) -> AssignmentResponse:
    """Assign a finding to a team member for remediation."""
    workspace_id = _resolve_workspace_id(current_user)
    return await svc.assign_finding(finding_id, workspace_id, req, current_user)


@router.get("/{finding_id}/assignment", response_model=AssignmentResponse)
async def get_assignment(
    finding_id: uuid.UUID,
    current_user: CurrentUserDep,
    svc: AssignmentService = Depends(_assignment_svc),
) -> AssignmentResponse:
    """Get the current active assignment for a finding."""
    workspace_id = _resolve_workspace_id(current_user)
    assignment = await svc.get_assignment(finding_id, workspace_id)
    if assignment is None:
        raise NotFoundError(f"No active assignment for finding {finding_id}")
    return assignment


@router.delete("/{finding_id}/assignment", status_code=status.HTTP_204_NO_CONTENT)
async def unassign_finding(
    finding_id: uuid.UUID,
    current_user: CurrentUserDep,
    svc: AssignmentService = Depends(_assignment_svc),
) -> None:
    """Unassign (deactivate) the current assignment for a finding."""
    workspace_id = _resolve_workspace_id(current_user)
    removed = await svc.unassign_finding(finding_id, workspace_id)
    if not removed:
        raise NotFoundError(f"No active assignment for finding {finding_id}")


@router.get("/{finding_id}/comments", response_model=list[FindingCommentResponse])
async def list_comments(
    finding_id: uuid.UUID,
    current_user: CurrentUserDep,
    svc: FindingCommentService = Depends(_comment_svc),
) -> list[FindingCommentResponse]:
    workspace_id = _resolve_workspace_id(current_user)
    return await svc.list_comments(finding_id, workspace_id)


@router.post(
    "/{finding_id}/comments",
    response_model=FindingCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_comment(
    finding_id: uuid.UUID,
    req: FindingCommentCreate,
    current_user: CurrentUserDep,
    svc: FindingCommentService = Depends(_comment_svc),
) -> FindingCommentResponse:
    workspace_id = _resolve_workspace_id(current_user)
    return await svc.add_comment(finding_id, current_user.id, workspace_id, req)


@router.delete(
    "/{finding_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_comment(
    finding_id: uuid.UUID,
    comment_id: uuid.UUID,
    current_user: CurrentUserDep,
    svc: FindingCommentService = Depends(_comment_svc),
) -> None:
    workspace_id = _resolve_workspace_id(current_user)
    deleted = await svc.delete_comment(comment_id, workspace_id, current_user.id)
    if not deleted:
        raise NotFoundError(f"Comment {comment_id} not found or not owned by current user")


@router.get("/{finding_id}", response_model=CanonicalFindingResponse)
async def get_finding(
    finding_id: uuid.UUID,
    current_user: CurrentUserDep,
    svc: FindingsService = Depends(_svc),
) -> CanonicalFindingResponse:
    workspace_id = _resolve_workspace_id(current_user)
    finding = await svc.get_finding(finding_id, workspace_id)
    return CanonicalFindingResponse.model_validate(finding)


@router.patch("/{finding_id}", response_model=CanonicalFindingResponse)
async def update_finding(
    finding_id: uuid.UUID,
    req: FindingUpdateRequest,
    current_user: CurrentUserDep,
    svc: FindingsService = Depends(_svc),
) -> CanonicalFindingResponse:
    workspace_id = _resolve_workspace_id(current_user)
    finding = await svc.update_finding(finding_id, workspace_id, req)
    return CanonicalFindingResponse.model_validate(finding)


def _risk_label(severity: str) -> str:
    mapping = {
        "critical": "critical-risk",
        "high": "high-risk",
        "medium": "medium-risk",
        "low": "low-risk",
        "info": "info",
    }
    return mapping.get(severity, "info")
