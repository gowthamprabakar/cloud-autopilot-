"""
Attack Path Visualization service — Sprint 27.

Provides attack-path chain building, blast-radius BFS traversal,
path detail retrieval, and workspace-level summary statistics.
"""

import json
import uuid
from collections import defaultdict, Counter

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attack_path import AttackPath
from app.models.security_graph_node import SecurityGraphNode
from app.models.security_graph_edge import SecurityGraphEdge


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_json(val):
    """Safely parse a JSON column that may already be deserialized."""
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    try:
        return json.loads(str(val))
    except Exception:
        return None


def _node_dict(node: SecurityGraphNode) -> dict:
    return {
        "id": str(node.id),
        "node_type": node.node_type,
        "resource_name": node.resource_name,
        "resource_arn": node.resource_arn,
        "region": node.region,
        "risk_score": node.risk_score,
        "is_internet_facing": node.is_internet_facing,
        "metadata": _parse_json(node.node_metadata),
        "finding_ids": _parse_json(node.finding_ids),
    }


def _edge_dict(edge: SecurityGraphEdge) -> dict:
    return {
        "id": str(edge.id),
        "source_node_id": str(edge.source_node_id),
        "target_node_id": str(edge.target_node_id),
        "edge_type": edge.edge_type,
        "is_attack_path": edge.is_attack_path,
        "risk_contribution": edge.risk_contribution,
        "metadata": _parse_json(edge.edge_metadata),
    }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class AttackPathService:
    """Workspace-scoped attack-path analytics."""

    def __init__(self, db: AsyncSession):
        self._db = db

    # ── 1. List attack paths ──────────────────────────────────────────────

    async def get_attack_paths(self, workspace_id: uuid.UUID) -> list[dict]:
        """
        Return all materialized AttackPath rows for the workspace,
        enriched with resolved node / edge details.
        """
        result = await self._db.execute(
            select(AttackPath)
            .where(
                AttackPath.workspace_id == workspace_id,
                AttackPath.is_active.is_(True),
            )
            .order_by(AttackPath.created_at.desc())
        )
        paths = result.scalars().all()

        # Collect all referenced node/edge ids for batch lookup
        all_node_ids: set[str] = set()
        all_edge_ids: set[str] = set()
        for p in paths:
            node_path = _parse_json(p.node_path) or []
            edge_path = _parse_json(p.edge_path) or []
            all_node_ids.update(str(n) for n in node_path)
            all_edge_ids.update(str(e) for e in edge_path)

        nodes_map = await self._load_nodes(all_node_ids)
        edges_map = await self._load_edges(all_edge_ids)

        out: list[dict] = []
        for p in paths:
            node_ids = [str(n) for n in (_parse_json(p.node_path) or [])]
            edge_ids = [str(e) for e in (_parse_json(p.edge_path) or [])]

            cumulative_risk = sum(
                (edges_map[eid].get("risk_contribution") or 0)
                for eid in edge_ids
                if eid in edges_map
            )

            out.append({
                "id": str(p.id),
                "name": p.name,
                "description": p.description,
                "severity": p.severity,
                "blast_radius": p.blast_radius,
                "toxic_combo_tags": _parse_json(p.toxic_combo_tags) or [],
                "entry_node_id": str(p.entry_node_id) if p.entry_node_id else None,
                "target_node_id": str(p.target_node_id) if p.target_node_id else None,
                "entry_description": p.entry_description,
                "target_description": p.target_description,
                "cumulative_risk": round(cumulative_risk, 4),
                "chain_length": len(node_ids),
                "nodes": [nodes_map[nid] for nid in node_ids if nid in nodes_map],
                "edges": [edges_map[eid] for eid in edge_ids if eid in edges_map],
                "related_finding_ids": _parse_json(p.related_finding_ids) or [],
                "created_at": p.created_at.isoformat() if p.created_at else None,
            })
        return out

    # ── 2. Blast radius (BFS) ─────────────────────────────────────────────

    async def get_blast_radius(
        self, workspace_id: uuid.UUID, node_id: uuid.UUID
    ) -> dict:
        """
        BFS from *node_id* along outgoing edges to find every reachable node.
        Returns the origin node, all reachable nodes, and traversed edges.
        """
        # Load all edges for the workspace once
        result = await self._db.execute(
            select(SecurityGraphEdge).where(
                SecurityGraphEdge.workspace_id == workspace_id
            )
        )
        edges = result.scalars().all()

        # Build adjacency list: source → [(target, edge)]
        adj: dict[str, list[tuple[str, SecurityGraphEdge]]] = defaultdict(list)
        for e in edges:
            adj[str(e.source_node_id)].append((str(e.target_node_id), e))

        # BFS
        start = str(node_id)
        visited: set[str] = set()
        queue: list[str] = [start]
        visited.add(start)
        traversed_edges: list[dict] = []

        while queue:
            current = queue.pop(0)
            for neighbor, edge in adj.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
                traversed_edges.append(_edge_dict(edge))

        # Remove origin from reachable set
        reachable_ids = visited - {start}

        # Load all reachable nodes + origin
        nodes_map = await self._load_nodes(visited)

        return {
            "origin": nodes_map.get(start),
            "reachable_count": len(reachable_ids),
            "reachable_nodes": [
                nodes_map[nid] for nid in reachable_ids if nid in nodes_map
            ],
            "edges": traversed_edges,
        }

    # ── 3. Single path detail ─────────────────────────────────────────────

    async def get_path_detail(
        self, workspace_id: uuid.UUID, path_id: uuid.UUID
    ) -> dict | None:
        """Return a single AttackPath with fully resolved nodes and edges."""
        result = await self._db.execute(
            select(AttackPath).where(
                AttackPath.id == path_id,
                AttackPath.workspace_id == workspace_id,
            )
        )
        path = result.scalar_one_or_none()
        if path is None:
            return None

        node_ids = [str(n) for n in (_parse_json(path.node_path) or [])]
        edge_ids = [str(e) for e in (_parse_json(path.edge_path) or [])]

        nodes_map = await self._load_nodes(set(node_ids))
        edges_map = await self._load_edges(set(edge_ids))

        cumulative_risk = sum(
            (edges_map[eid].get("risk_contribution") or 0)
            for eid in edge_ids
            if eid in edges_map
        )

        return {
            "id": str(path.id),
            "name": path.name,
            "description": path.description,
            "severity": path.severity,
            "blast_radius": path.blast_radius,
            "toxic_combo_tags": _parse_json(path.toxic_combo_tags) or [],
            "entry_node_id": str(path.entry_node_id) if path.entry_node_id else None,
            "target_node_id": str(path.target_node_id) if path.target_node_id else None,
            "entry_description": path.entry_description,
            "target_description": path.target_description,
            "cumulative_risk": round(cumulative_risk, 4),
            "chain_length": len(node_ids),
            "nodes": [nodes_map[nid] for nid in node_ids if nid in nodes_map],
            "edges": [edges_map[eid] for eid in edge_ids if eid in edges_map],
            "related_finding_ids": _parse_json(path.related_finding_ids) or [],
            "is_active": path.is_active,
            "created_at": path.created_at.isoformat() if path.created_at else None,
            "updated_at": path.updated_at.isoformat() if path.updated_at else None,
        }

    # ── 4. Summary stats ──────────────────────────────────────────────────

    async def summary(self, workspace_id: uuid.UUID) -> dict:
        """
        Workspace-level attack-path statistics:
        total paths, critical count, avg risk, most targeted node, longest chain.
        """
        result = await self._db.execute(
            select(AttackPath).where(
                AttackPath.workspace_id == workspace_id,
                AttackPath.is_active.is_(True),
            )
        )
        paths = result.scalars().all()

        if not paths:
            return {
                "total_paths": 0,
                "critical_paths": 0,
                "high_paths": 0,
                "medium_paths": 0,
                "low_paths": 0,
                "avg_risk": 0.0,
                "most_targeted_node_id": None,
                "most_targeted_node_name": None,
                "most_targeted_count": 0,
                "longest_chain_length": 0,
                "longest_chain_path_id": None,
            }

        # Collect all edge ids for risk calculation
        all_edge_ids: set[str] = set()
        for p in paths:
            edge_path = _parse_json(p.edge_path) or []
            all_edge_ids.update(str(e) for e in edge_path)
        edges_map = await self._load_edges(all_edge_ids)

        severity_counts = Counter(p.severity for p in paths)
        target_counts: Counter = Counter()
        longest_chain = 0
        longest_chain_path_id: str | None = None
        total_risk = 0.0

        for p in paths:
            node_ids = _parse_json(p.node_path) or []
            edge_ids = [str(e) for e in (_parse_json(p.edge_path) or [])]

            chain_len = len(node_ids)
            if chain_len > longest_chain:
                longest_chain = chain_len
                longest_chain_path_id = str(p.id)

            path_risk = sum(
                (edges_map[eid].get("risk_contribution") or 0)
                for eid in edge_ids
                if eid in edges_map
            )
            total_risk += path_risk

            if p.target_node_id:
                target_counts[str(p.target_node_id)] += 1

        avg_risk = round(total_risk / len(paths), 4) if paths else 0.0

        most_targeted_id: str | None = None
        most_targeted_name: str | None = None
        most_targeted_count = 0
        if target_counts:
            most_targeted_id = target_counts.most_common(1)[0][0]
            most_targeted_count = target_counts.most_common(1)[0][1]
            # Resolve name
            node_map = await self._load_nodes({most_targeted_id})
            node = node_map.get(most_targeted_id)
            if node:
                most_targeted_name = node.get("resource_name")

        return {
            "total_paths": len(paths),
            "critical_paths": severity_counts.get("critical", 0),
            "high_paths": severity_counts.get("high", 0),
            "medium_paths": severity_counts.get("medium", 0),
            "low_paths": severity_counts.get("low", 0),
            "avg_risk": avg_risk,
            "most_targeted_node_id": most_targeted_id,
            "most_targeted_node_name": most_targeted_name,
            "most_targeted_count": most_targeted_count,
            "longest_chain_length": longest_chain,
            "longest_chain_path_id": longest_chain_path_id,
        }

    # ── Internal helpers ──────────────────────────────────────────────────

    async def _load_nodes(self, node_ids: set[str]) -> dict[str, dict]:
        """Batch-load SecurityGraphNode rows by id, return {str_id: dict}."""
        if not node_ids:
            return {}
        uuids = [uuid.UUID(nid) for nid in node_ids]
        result = await self._db.execute(
            select(SecurityGraphNode).where(SecurityGraphNode.id.in_(uuids))
        )
        return {str(n.id): _node_dict(n) for n in result.scalars().all()}

    async def _load_edges(self, edge_ids: set[str]) -> dict[str, dict]:
        """Batch-load SecurityGraphEdge rows by id, return {str_id: dict}."""
        if not edge_ids:
            return {}
        uuids = [uuid.UUID(eid) for eid in edge_ids]
        result = await self._db.execute(
            select(SecurityGraphEdge).where(SecurityGraphEdge.id.in_(uuids))
        )
        return {str(e.id): _edge_dict(e) for e in result.scalars().all()}
