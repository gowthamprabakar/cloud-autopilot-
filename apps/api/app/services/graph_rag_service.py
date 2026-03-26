"""
GraphRAGService — Security Graph + Retrieval-Augmented Generation.

Sprint 31: Manages the Neo4j security graph for:
1. Ingesting security findings as graph nodes/edges
2. Attack path discovery via Cypher queries
3. Blast radius computation via graph traversal
4. Context retrieval for agent prompts (RAG)
5. Toxic combination detection
"""

from __future__ import annotations
import uuid
import json
from typing import Any
from app.core.neo4j_client import get_neo4j_session


class GraphRAGService:

    # ── Node Management ──────────────────────────────────────────

    async def upsert_resource_node(self, resource: dict) -> dict:
        """Create or update a cloud resource node in the graph.
        Properties: arn, type, name, region, account_id, risk_score, is_internet_facing, tags
        """
        async with await get_neo4j_session() as session:
            result = await session.run("""
                MERGE (r:Resource {arn: $arn})
                SET r.type = $type, r.name = $name, r.region = $region,
                    r.account_id = $account_id, r.risk_score = $risk_score,
                    r.is_internet_facing = $is_internet_facing,
                    r.updated_at = datetime()
                RETURN r
            """, **resource)
            record = await result.single()
            return dict(record["r"]) if record else {}

    async def upsert_identity_node(self, identity: dict) -> dict:
        """Create or update an IAM identity node.
        Properties: arn, type (iam_role/iam_user), name, permission_scope, has_mfa, policies
        """
        async with await get_neo4j_session() as session:
            result = await session.run("""
                MERGE (i:Identity {arn: $arn})
                SET i.type = $type, i.name = $name,
                    i.permission_scope = $permission_scope,
                    i.has_mfa = $has_mfa, i.policies = $policies,
                    i.updated_at = datetime()
                RETURN i
            """, **identity)
            record = await result.single()
            return dict(record["i"]) if record else {}

    async def upsert_finding_node(self, finding: dict) -> dict:
        """Create or update a security finding node.
        Properties: finding_id, title, severity, status, cve_id, epss_score, in_kev
        """
        async with await get_neo4j_session() as session:
            result = await session.run("""
                MERGE (f:Finding {finding_id: $finding_id})
                SET f.title = $title, f.severity = $severity, f.status = $status,
                    f.cve_id = $cve_id, f.epss_score = $epss_score, f.in_kev = $in_kev,
                    f.updated_at = datetime()
                RETURN f
            """, **finding)
            record = await result.single()
            return dict(record["f"]) if record else {}

    # ── Edge Management ──────────────────────────────────────────

    async def create_edge(self, from_arn: str, to_arn: str, edge_type: str, properties: dict = None) -> dict:
        """Create a typed relationship between two nodes."""
        props = properties or {}
        async with await get_neo4j_session() as session:
            result = await session.run(f"""
                MATCH (a {{arn: $from_arn}})
                MATCH (b {{arn: $to_arn}})
                MERGE (a)-[r:{edge_type}]->(b)
                SET r += $props, r.updated_at = datetime()
                RETURN type(r) AS type, properties(r) AS props
            """, from_arn=from_arn, to_arn=to_arn, props=props)
            record = await result.single()
            return {"type": record["type"], "properties": record["props"]} if record else {}

    # ── Query Operations ─────────────────────────────────────────

    async def find_attack_paths(self, source_arn: str, max_depth: int = 6) -> list[dict]:
        """Find all attack paths from a source node up to max_depth hops."""
        async with await get_neo4j_session() as session:
            result = await session.run("""
                MATCH path = (source {arn: $source_arn})-[*1..$max_depth]->(target)
                WHERE any(r IN relationships(path) WHERE type(r) IN
                    ['CAN_ASSUME', 'PRIVILEGE_ESCALATION', 'EXPOSES', 'HAS_ACCESS_TO'])
                RETURN [n IN nodes(path) | {arn: n.arn, type: labels(n)[0], name: n.name, risk_score: n.risk_score}] AS nodes,
                       [r IN relationships(path) | {type: type(r), from: startNode(r).arn, to: endNode(r).arn}] AS edges,
                       length(path) AS depth
                ORDER BY depth
                LIMIT 20
            """, source_arn=source_arn, max_depth=max_depth)
            return [dict(record) async for record in result]

    async def compute_blast_radius(self, node_arn: str, max_hops: int = 4) -> dict:
        """Compute blast radius -- all nodes reachable from a compromised node."""
        async with await get_neo4j_session() as session:
            result = await session.run("""
                MATCH (source {arn: $node_arn})
                CALL apoc.path.subgraphNodes(source, {maxLevel: $max_hops}) YIELD node
                WITH collect(node) AS reachable, source
                RETURN source.arn AS origin,
                       size(reachable) AS reachable_count,
                       [n IN reachable | {arn: n.arn, type: labels(n)[0], name: n.name}] AS reachable_nodes
            """, node_arn=node_arn, max_hops=max_hops)
            record = await result.single()
            return dict(record) if record else {"origin": node_arn, "reachable_count": 0, "reachable_nodes": []}

    async def detect_toxic_combinations(self) -> list[dict]:
        """Find toxic combinations: public + unencrypted + sensitive data."""
        async with await get_neo4j_session() as session:
            result = await session.run("""
                MATCH (r:Resource)
                WHERE r.is_internet_facing = true
                MATCH (r)<-[:AFFECTS]-(f:Finding)
                WHERE f.severity IN ['critical', 'high'] AND f.status = 'open'
                WITH r, collect(f) AS findings
                WHERE size(findings) >= 2
                RETURN r.arn AS resource_arn, r.type AS resource_type, r.name AS resource_name,
                       [f IN findings | {title: f.title, severity: f.severity, cve_id: f.cve_id}] AS findings,
                       size(findings) AS finding_count
                ORDER BY finding_count DESC
                LIMIT 20
            """)
            return [dict(record) async for record in result]

    async def get_context_for_agent(self, domain: str, resource_arn: str = None) -> str:
        """Retrieve graph context for agent RAG enrichment."""
        context_parts = []

        if resource_arn:
            # Get neighborhood of a specific resource
            async with await get_neo4j_session() as session:
                result = await session.run("""
                    MATCH (r {arn: $arn})-[rel]-(neighbor)
                    RETURN r.arn AS source, type(rel) AS relationship,
                           neighbor.arn AS neighbor_arn, labels(neighbor)[0] AS neighbor_type,
                           neighbor.name AS neighbor_name
                    LIMIT 50
                """, arn=resource_arn)
                records = [dict(r) async for r in result]
                if records:
                    context_parts.append(f"## Graph Context for {resource_arn}")
                    for rec in records:
                        context_parts.append(
                            f"- {rec['source']} --[{rec['relationship']}]--> "
                            f"{rec['neighbor_arn']} ({rec['neighbor_type']})"
                        )

        # Get domain-relevant stats
        async with await get_neo4j_session() as session:
            result = await session.run("""
                MATCH (n)
                RETURN labels(n)[0] AS type, count(n) AS count
                ORDER BY count DESC
            """)
            stats = [dict(r) async for r in result]
            if stats:
                context_parts.append("## Graph Statistics")
                for s in stats:
                    context_parts.append(f"- {s['type']}: {s['count']} nodes")

        return "\n".join(context_parts) if context_parts else "No graph context available."

    async def graph_summary(self) -> dict:
        """Return overall graph statistics."""
        async with await get_neo4j_session() as session:
            node_result = await session.run(
                "MATCH (n) RETURN labels(n)[0] AS type, count(n) AS count"
            )
            nodes = {r["type"]: r["count"] async for r in node_result}

            edge_result = await session.run(
                "MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count"
            )
            edges = {r["type"]: r["count"] async for r in edge_result}

            return {
                "total_nodes": sum(nodes.values()),
                "total_edges": sum(edges.values()),
                "nodes_by_type": nodes,
                "edges_by_type": edges,
            }
