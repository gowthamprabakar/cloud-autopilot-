"""
AttackPathAnalyzerAgent — BFS-based security graph traversal.

For a given finding, identifies all linked graph nodes, walks the security graph
up to 3 hops via BFS, computes blast radius and choke points,
then generates a natural language summary via Ollama llama3.

Extends BaseAgent: timing, audit logging, and result persistence are inherited.
"""

import uuid
from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.security_graph_node import SecurityGraphNode
from app.repositories.security_graph_repository import SecurityGraphRepository
from app.services.agents.base_agent import BaseAgent

# Nodes with degree > this threshold are flagged as choke points
_CHOKE_POINT_DEGREE_THRESHOLD = 3
_MAX_BFS_HOPS = 3
_MAX_CHAIN_LENGTH = 6  # cap attack chain display length


class AttackPathAnalyzerAgent(BaseAgent):
    """
    Analyzes the blast radius of a finding through the security graph.

    Output shape:
    {
        "blast_radius_count": int,       # reachable nodes within 3 hops
        "choke_points": list[str],       # high-degree node labels
        "path_summary": str,             # Ollama-generated NL narrative
        "attack_chain": list[str],       # seed + top-N reachable by risk_score
    }
    """
    agent_name = "attack_path"

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self._graph_repo = SecurityGraphRepository(db)

    async def _run(
        self, finding_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> tuple[dict, str]:
        finding_id_str = str(finding_id)

        # ── Step 1: Find seed nodes linked to this finding ───────────────────
        result = await self.db.execute(
            select(SecurityGraphNode).where(
                SecurityGraphNode.workspace_id == workspace_id,
            )
        )
        all_nodes = list(result.scalars().all())
        seed_nodes = [
            n for n in all_nodes
            if finding_id_str in (n.finding_ids or [])
        ]

        if not seed_nodes:
            output = {
                "blast_radius_count": 0,
                "choke_points": [],
                "path_summary": (
                    "No graph nodes are linked to this finding. "
                    "The finding may be isolated or the security graph has not been built yet."
                ),
                "attack_chain": [],
            }
            return output, "none"

        # ── Step 2: BFS up to 3 hops from each seed ─────────────────────────
        reachable_ids: set[uuid.UUID] = set()
        for seed in seed_nodes:
            neighbors = await self._graph_repo.bfs_neighbors(seed.id, max_depth=_MAX_BFS_HOPS)
            reachable_ids.update(n.id for n in neighbors)

        blast_radius_count = len(reachable_ids)

        # ── Step 3: Load reachable node objects ───────────────────────────────
        reachable_nodes: list[SecurityGraphNode] = []
        for nid in reachable_ids:
            node_result = await self.db.execute(
                select(SecurityGraphNode).where(SecurityGraphNode.id == nid)
            )
            node = node_result.scalar_one_or_none()
            if node:
                reachable_nodes.append(node)

        # ── Step 4: Identify choke points by edge degree ─────────────────────
        degree_counter: Counter = Counter()
        candidate_ids = {s.id for s in seed_nodes} | reachable_ids
        for nid in candidate_ids:
            edges = await self._graph_repo.get_edges_for_node(nid, direction="both")
            degree_counter[nid] = len(edges)

        def _label(node: SecurityGraphNode) -> str:
            return node.resource_name or node.resource_arn or str(node.id)

        choke_point_nodes = [
            n for n in (seed_nodes + reachable_nodes)
            if degree_counter.get(n.id, 0) > _CHOKE_POINT_DEGREE_THRESHOLD
        ]
        choke_points = list({_label(n) for n in choke_point_nodes})

        # ── Step 5: Build attack chain (seeds → top reachable by risk_score) ─
        attack_chain: list[str] = [_label(n) for n in seed_nodes]
        sorted_reachable = sorted(
            reachable_nodes,
            key=lambda n: (n.risk_score or 0.0),
            reverse=True,
        )
        for n in sorted_reachable[:_MAX_CHAIN_LENGTH - len(seed_nodes)]:
            attack_chain.append(_label(n))

        # ── Step 6: Ollama NL summary ─────────────────────────────────────────
        path_summary = await self._generate_summary(
            seed_nodes=seed_nodes,
            blast_radius_count=blast_radius_count,
            choke_points=choke_points,
            attack_chain=attack_chain,
        )

        output = {
            "blast_radius_count": blast_radius_count,
            "choke_points": choke_points,
            "path_summary": path_summary,
            "attack_chain": attack_chain,
        }
        return output, "ollama/llama3"

    async def _generate_summary(
        self,
        seed_nodes: list[SecurityGraphNode],
        blast_radius_count: int,
        choke_points: list[str],
        attack_chain: list[str],
    ) -> str:
        """Generate an NL narrative via Ollama llama3. Falls back to rule-based text."""
        import httpx
        import json

        seed_descriptions = ", ".join(
            f"{n.node_type}:{n.resource_name or n.resource_arn or 'unknown'}"
            for n in seed_nodes[:3]
        )
        prompt = (
            "You are a cloud security analyst. Summarize the following attack path analysis "
            "in 3-4 sentences for a security engineer. Focus on: what resources are at risk, "
            "how an attacker could move laterally through the graph, and which choke points "
            "to prioritize for remediation.\n\n"
            f"Entry nodes (directly affected by finding): {seed_descriptions}\n"
            f"Blast radius (resources reachable within 3 hops): {blast_radius_count}\n"
            f"Choke points (high-connectivity nodes): {', '.join(choke_points) or 'None identified'}\n"
            f"Attack chain (entry → high-risk path): {' → '.join(attack_chain[:6]) or 'N/A'}\n\n"
            'Return a JSON object with a single key "path_summary" containing your narrative.'
        )
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                resp = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "llama3",
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                raw = data.get("response", "{}")
                parsed = json.loads(raw) if isinstance(raw, str) else raw
                summary = parsed.get("path_summary", "")
                if summary:
                    return summary
        except Exception:
            pass  # Fall through to rule-based fallback

        return self._rule_based_summary(blast_radius_count, choke_points, seed_nodes)

    @staticmethod
    def _rule_based_summary(
        blast_radius_count: int,
        choke_points: list[str],
        seed_nodes: list[SecurityGraphNode],
    ) -> str:
        """Deterministic fallback summary when Ollama is unavailable."""
        seed_label = seed_nodes[0].node_type if seed_nodes else "resource"
        cp_text = (
            f" Prioritize remediation at choke points: {', '.join(choke_points[:3])}."
            if choke_points
            else ""
        )
        return (
            f"This finding is linked to a {seed_label} that can reach "
            f"{blast_radius_count} additional cloud resource(s) within 3 hops "
            f"through the security graph.{cp_text} "
            "Immediate remediation is recommended to contain the blast radius."
        )
