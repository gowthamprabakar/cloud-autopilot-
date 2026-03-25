"""
SecurityGraphEdge — directed relationship between two SecurityGraphNodes.

Each edge has a typed relationship (exposes, has_access_to, assumes_role, etc.)
and can be flagged as part of an active attack path with a risk contribution score.
"""

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Index, String
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class SecurityGraphEdge(Base, UUIDPKMixin, TimestampMixin):
    """
    A directed edge in the workspace security graph.
    source_node → target_node with a typed relationship and optional risk metadata.
    """

    __tablename__ = "security_graph_edges"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("security_graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("security_graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Edge type — the semantic relationship between source and target
    # Values: "exposes"|"has_access_to"|"is_attached_to"|"connects_to"|
    #         "assumes_role"|"stores_data_in"|"reads_from"|"writes_to"|
    #         "triggers"|"manages"
    edge_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # True when this edge is part of an active attack path
    is_attack_path: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )

    # 0.0–1.0 — how much this edge contributes to overall path risk
    risk_contribution: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Freeform edge metadata (e.g., port numbers, protocol, rule details)
    edge_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)

    # Relationships
    source_node: Mapped["SecurityGraphNode"] = relationship(  # type: ignore[name-defined]
        "SecurityGraphNode",
        foreign_keys=[source_node_id],
        lazy="select",
    )
    target_node: Mapped["SecurityGraphNode"] = relationship(  # type: ignore[name-defined]
        "SecurityGraphNode",
        foreign_keys=[target_node_id],
        lazy="select",
    )

    __table_args__ = (
        Index("ix_sge_workspace_attack_path", "workspace_id", "is_attack_path"),
        Index("ix_sge_source_target", "source_node_id", "target_node_id"),
    )

    def __repr__(self) -> str:
        return f"<SecurityGraphEdge {self.edge_type} {self.source_node_id}→{self.target_node_id}>"
