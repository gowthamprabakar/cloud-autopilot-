"""
SecurityGraphRepository — data access layer for security graph nodes, edges,
and attack paths.

All queries are workspace-scoped. No business logic lives here — only
data access and graph traversal queries.
"""

import uuid
from collections import deque

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attack_path import AttackPath
from app.models.security_graph_edge import SecurityGraphEdge
from app.models.security_graph_node import SecurityGraphNode

logger = structlog.get_logger(__name__)


class SecurityGraphRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Node operations ────────────────────────────────────────────────────

    async def create_node(self, **kwargs) -> SecurityGraphNode:
        """Create and persist a new security graph node."""
        node = SecurityGraphNode(**kwargs)
        self.db.add(node)
        await self.db.flush()
        await self.db.refresh(node)
        return node

    async def get_node(
        self, node_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> SecurityGraphNode | None:
        """Fetch a single node by ID, scoped to workspace."""
        result = await self.db.execute(
            select(SecurityGraphNode).where(
                SecurityGraphNode.id == node_id,
                SecurityGraphNode.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_nodes_by_workspace(
        self, workspace_id: uuid.UUID
    ) -> list[SecurityGraphNode]:
        """Return all nodes for a workspace ordered by creation time."""
        result = await self.db.execute(
            select(SecurityGraphNode)
            .where(SecurityGraphNode.workspace_id == workspace_id)
            .order_by(SecurityGraphNode.created_at)
        )
        return list(result.scalars().all())

    async def get_node_by_arn(
        self, resource_arn: str, workspace_id: uuid.UUID
    ) -> SecurityGraphNode | None:
        """Find a node by its ARN within a workspace."""
        result = await self.db.execute(
            select(SecurityGraphNode).where(
                SecurityGraphNode.resource_arn == resource_arn,
                SecurityGraphNode.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_node_findings(
        self, node_id: uuid.UUID, finding_ids: list[str]
    ) -> SecurityGraphNode:
        """Replace the finding_ids list on a node and return the updated node."""
        result = await self.db.execute(
            select(SecurityGraphNode).where(SecurityGraphNode.id == node_id)
        )
        node = result.scalar_one_or_none()
        if node is None:
            from app.core.exceptions import NotFoundError
            raise NotFoundError(f"SecurityGraphNode {node_id} not found")
        node.finding_ids = finding_ids
        await self.db.flush()
        await self.db.refresh(node)
        return node

    async def delete_node(self, node_id: uuid.UUID) -> bool:
        """Delete a node by ID. Returns True if a row was deleted."""
        result = await self.db.execute(
            select(SecurityGraphNode).where(SecurityGraphNode.id == node_id)
        )
        node = result.scalar_one_or_none()
        if node is None:
            return False
        await self.db.delete(node)
        await self.db.flush()
        return True

    # ── Edge operations ────────────────────────────────────────────────────

    async def create_edge(self, **kwargs) -> SecurityGraphEdge:
        """Create and persist a new security graph edge."""
        edge = SecurityGraphEdge(**kwargs)
        self.db.add(edge)
        await self.db.flush()
        await self.db.refresh(edge)
        return edge

    async def get_edges_by_workspace(
        self, workspace_id: uuid.UUID
    ) -> list[SecurityGraphEdge]:
        """Return all edges for a workspace."""
        result = await self.db.execute(
            select(SecurityGraphEdge)
            .where(SecurityGraphEdge.workspace_id == workspace_id)
            .order_by(SecurityGraphEdge.created_at)
        )
        return list(result.scalars().all())

    async def get_edges_for_node(
        self, node_id: uuid.UUID, direction: str = "both"
    ) -> list[SecurityGraphEdge]:
        """
        Return edges for a given node.
        direction: "outgoing" | "incoming" | "both"
        """
        if direction == "outgoing":
            condition = SecurityGraphEdge.source_node_id == node_id
        elif direction == "incoming":
            condition = SecurityGraphEdge.target_node_id == node_id
        else:
            from sqlalchemy import or_
            condition = or_(
                SecurityGraphEdge.source_node_id == node_id,
                SecurityGraphEdge.target_node_id == node_id,
            )

        result = await self.db.execute(
            select(SecurityGraphEdge).where(condition)
        )
        return list(result.scalars().all())

    async def get_attack_path_edges(
        self, workspace_id: uuid.UUID
    ) -> list[SecurityGraphEdge]:
        """Return only edges flagged as part of an attack path."""
        result = await self.db.execute(
            select(SecurityGraphEdge).where(
                SecurityGraphEdge.workspace_id == workspace_id,
                SecurityGraphEdge.is_attack_path.is_(True),
            )
        )
        return list(result.scalars().all())

    # ── Attack path operations ─────────────────────────────────────────────

    async def create_attack_path(self, **kwargs) -> AttackPath:
        """Create and persist a new attack path."""
        path = AttackPath(**kwargs)
        self.db.add(path)
        await self.db.flush()
        await self.db.refresh(path)
        return path

    async def get_attack_paths(
        self, workspace_id: uuid.UUID, active_only: bool = True
    ) -> list[AttackPath]:
        """Return all attack paths for a workspace, optionally filtered to active."""
        stmt = select(AttackPath).where(AttackPath.workspace_id == workspace_id)
        if active_only:
            stmt = stmt.where(AttackPath.is_active.is_(True))
        stmt = stmt.order_by(AttackPath.created_at)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_attack_path(
        self, path_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> AttackPath | None:
        """Fetch a single attack path by ID, scoped to workspace."""
        result = await self.db.execute(
            select(AttackPath).where(
                AttackPath.id == path_id,
                AttackPath.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    # ── Graph query operations ─────────────────────────────────────────────

    async def get_full_graph(
        self, workspace_id: uuid.UUID
    ) -> tuple[list[SecurityGraphNode], list[SecurityGraphEdge]]:
        """Return all nodes and edges for a workspace in a single pair of queries."""
        nodes = await self.get_nodes_by_workspace(workspace_id)
        edges = await self.get_edges_by_workspace(workspace_id)
        return nodes, edges

    async def bfs_neighbors(
        self, start_node_id: uuid.UUID, max_depth: int = 5
    ) -> list[SecurityGraphNode]:
        """
        Breadth-first traversal from start_node_id up to max_depth hops.
        Returns all reachable nodes (excluding the start node itself).
        Loads edges incrementally to avoid fetching the full graph.
        """
        visited: set[uuid.UUID] = {start_node_id}
        frontier: deque[tuple[uuid.UUID, int]] = deque([(start_node_id, 0)])
        result_nodes: list[SecurityGraphNode] = []

        while frontier:
            current_id, depth = frontier.popleft()
            if depth >= max_depth:
                continue

            # Get outgoing edges from the current node
            outgoing = await self.get_edges_for_node(current_id, direction="outgoing")
            for edge in outgoing:
                neighbor_id = edge.target_node_id
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    # Fetch the neighbor node
                    node_result = await self.db.execute(
                        select(SecurityGraphNode).where(
                            SecurityGraphNode.id == neighbor_id
                        )
                    )
                    node = node_result.scalar_one_or_none()
                    if node is not None:
                        result_nodes.append(node)
                        frontier.append((neighbor_id, depth + 1))

        return result_nodes

    async def get_nodes_on_attack_paths(
        self, workspace_id: uuid.UUID
    ) -> set[str]:
        """
        Return the set of node ID strings that appear in any active attack path
        for the given workspace. Used for stats and highlighting.
        """
        paths = await self.get_attack_paths(workspace_id, active_only=True)
        node_ids: set[str] = set()
        for path in paths:
            for nid in path.node_path:
                node_ids.add(str(nid))
        return node_ids

    async def clear_workspace_graph(self, workspace_id: uuid.UUID) -> None:
        """
        Delete all nodes, edges, and attack paths for a workspace.
        Edges are cascade-deleted when nodes are deleted (via FK CASCADE).
        Attack paths are deleted first to avoid FK constraint issues.
        """
        # Delete attack paths first (FK references to nodes)
        await self.db.execute(
            delete(AttackPath).where(AttackPath.workspace_id == workspace_id)
        )
        # Delete edges (also cascade via node deletion, but explicit is safer)
        await self.db.execute(
            delete(SecurityGraphEdge).where(
                SecurityGraphEdge.workspace_id == workspace_id
            )
        )
        # Delete nodes
        await self.db.execute(
            delete(SecurityGraphNode).where(
                SecurityGraphNode.workspace_id == workspace_id
            )
        )
        await self.db.flush()
