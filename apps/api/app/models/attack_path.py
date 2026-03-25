"""
AttackPath — a materialized, ordered chain of nodes and edges describing
how an attacker can traverse the security graph from an entry point to a
sensitive target resource.

Toxic combo tags describe the confluence of misconfigurations that enable
the path (e.g. public_access + overpermissioned_iam + unencrypted_rds).
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class AttackPath(Base, UUIDPKMixin, TimestampMixin):
    """
    Materialized attack path — ordered list of node/edge UUIDs forming a
    traversal from entry to sensitive target with associated risk metadata.
    """

    __tablename__ = "attack_paths"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Severity mirrors FindingSeverity values: critical|high|medium|low|info
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    # Ordered lists of UUIDs (as strings) describing the traversal
    node_path: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    edge_path: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Tags describing the toxic combination of misconfigs enabling this path
    toxic_combo_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Count of sensitive resources reachable from this path
    blast_radius: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Entry and target node UUIDs — nullable for programmatic paths
    entry_node_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("security_graph_nodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_node_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("security_graph_nodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    entry_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )

    # Canonical finding UUIDs (as strings) that make this path possible
    related_finding_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    __table_args__ = (
        Index("ix_ap_workspace_active", "workspace_id", "is_active"),
        Index("ix_ap_workspace_severity", "workspace_id", "severity"),
    )

    def __repr__(self) -> str:
        return f"<AttackPath {self.severity} {self.name[:40]}>"
