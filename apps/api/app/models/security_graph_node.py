"""
SecurityGraphNode — represents a cloud resource vertex in the security graph.

Each node is a typed cloud resource (S3, IAM, EC2, RDS, etc.) with rich metadata,
risk scoring, and references to canonical findings that affect it.
"""

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Index, String, Text
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class SecurityGraphNode(Base, UUIDPKMixin, TimestampMixin):
    """
    A vertex in the workspace security graph.
    node_type controls which metadata fields are populated.
    """

    __tablename__ = "security_graph_nodes"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    aws_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("aws_accounts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Node type — controls which metadata fields are meaningful
    # Values: "s3_bucket"|"iam_role"|"lambda"|"rds"|"ec2"|"vpc"|
    #         "security_group"|"internet"|"subnet"|"kms_key"|
    #         "secrets_manager"|"cloudtrail"
    node_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    resource_arn: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    resource_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    region: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Rich per-resource-type metadata stored as JSON
    node_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)

    # List of canonical_finding UUIDs (as strings) linked to this node
    finding_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    is_internet_facing: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    is_sensitive_data: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Relationships — lazy="selectin" so graph queries load edges automatically
    outgoing_edges: Mapped[list["SecurityGraphEdge"]] = relationship(  # type: ignore[name-defined]
        "SecurityGraphEdge",
        foreign_keys="SecurityGraphEdge.source_node_id",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    incoming_edges: Mapped[list["SecurityGraphEdge"]] = relationship(  # type: ignore[name-defined]
        "SecurityGraphEdge",
        foreign_keys="SecurityGraphEdge.target_node_id",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_sgn_workspace_node_type", "workspace_id", "node_type"),
        Index("ix_sgn_workspace_internet_facing", "workspace_id", "is_internet_facing"),
    )

    def __repr__(self) -> str:
        return f"<SecurityGraphNode {self.node_type} {self.resource_name}>"
