"""
SecurityGraphService — business logic for the security graph.

Responsibilities:
- Assembling the full graph response with stats
- Resolving node findings from canonical_findings
- Seeding a realistic demo graph for onboarding/demo workspaces

Rules:
- workspace_id always scopes all operations.
- seed_demo_graph is idempotent — it clears the existing graph first.
- No raw SQL — all data access through SecurityGraphRepository.
"""

import uuid

import structlog

from app.models.attack_path import AttackPath
from app.repositories.security_graph_repository import SecurityGraphRepository
from app.schemas.security_graph import (
    AttackPathResponse,
    NodeFindingsResponse,
    SecurityGraphEdgeResponse,
    SecurityGraphNodeResponse,
    SecurityGraphResponse,
)

logger = structlog.get_logger(__name__)


class SecurityGraphService:
    def __init__(self, repo: SecurityGraphRepository) -> None:
        self._repo = repo

    async def get_graph(self, workspace_id: uuid.UUID) -> SecurityGraphResponse:
        """
        Return the full graph for a workspace: nodes, edges, attack paths, and stats.
        """
        nodes, edges = await self._repo.get_full_graph(workspace_id)
        attack_paths = await self._repo.get_attack_paths(workspace_id, active_only=False)
        attack_path_node_ids = await self._repo.get_nodes_on_attack_paths(workspace_id)

        node_responses = [
            SecurityGraphNodeResponse.model_validate(n) for n in nodes
        ]
        edge_responses = [
            SecurityGraphEdgeResponse.model_validate(e) for e in edges
        ]
        path_responses = [
            AttackPathResponse.model_validate(p) for p in attack_paths
        ]

        stats = {
            "total_nodes": len(nodes),
            "attack_path_nodes": len(attack_path_node_ids),
            "internet_facing": sum(1 for n in nodes if n.is_internet_facing),
            "sensitive_data_nodes": sum(1 for n in nodes if n.is_sensitive_data),
        }

        return SecurityGraphResponse(
            nodes=node_responses,
            edges=edge_responses,
            attack_paths=path_responses,
            stats=stats,
        )

    async def get_attack_paths(self, workspace_id: uuid.UUID) -> list[AttackPath]:
        """Return all active attack paths for a workspace."""
        return await self._repo.get_attack_paths(workspace_id, active_only=True)

    async def get_node_findings(
        self, node_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> NodeFindingsResponse:
        """
        Return the node metadata plus any canonical findings linked via finding_ids.

        For demo/seed nodes, finding_ids is an empty list so findings will be [].
        In production, finding IDs are populated by the normalization service.
        """
        node = await self._repo.get_node(node_id, workspace_id)
        if node is None:
            from app.core.exceptions import NotFoundError
            raise NotFoundError(f"SecurityGraphNode {node_id} not found")

        # If there are linked finding IDs, resolve them from canonical_findings.
        # We do a best-effort fetch — missing findings are silently skipped.
        findings = []
        if node.finding_ids:
            from sqlalchemy import select
            from app.models.canonical_finding import CanonicalFinding

            # Access the session through the repo
            result = await self._repo.db.execute(
                select(CanonicalFinding).where(
                    CanonicalFinding.id.in_(
                        [uuid.UUID(fid) for fid in node.finding_ids if fid]
                    ),
                    CanonicalFinding.workspace_id == workspace_id,
                )
            )
            db_findings = result.scalars().all()
            findings = [
                {
                    "id": str(f.id),
                    "title": f.title,
                    "severity": str(f.severity),
                    "status": str(f.status),
                    "risk_score": f.risk_score,
                    "resource_arn": f.resource_arn,
                    "description": f.description,
                    "remediation": f.remediation,
                }
                for f in db_findings
            ]

        return NodeFindingsResponse(
            node_id=node.id,
            node_type=node.node_type,
            resource_name=node.resource_name,
            findings=findings,
        )

    async def seed_demo_graph(
        self, workspace_id: uuid.UUID, aws_account_id: uuid.UUID
    ) -> dict:
        """
        Seed a realistic 18-node, 20-edge demo security graph.

        This method is idempotent — it clears any existing graph for the
        workspace before creating the demo data. Returns a summary dict.

        Graph scenario:
          - Two attack paths: Internet→S3→IAM→RDS (critical) and
            Internet→EC2→SG→RDS (high).
          - 18 nodes covering the common AWS resource types.
          - 20 edges with risk contributions and attack path flags.
        """
        logger.info("seed_demo_graph.start", workspace_id=str(workspace_id))

        # Wipe any pre-existing graph data for this workspace
        await self._repo.clear_workspace_graph(workspace_id)

        # ── Node creation helpers ──────────────────────────────────────────
        def _node_kwargs(
            node_type: str,
            resource_name: str,
            resource_arn: str | None = None,
            region: str | None = None,
            metadata: dict | None = None,
            risk_score: float | None = None,
            is_internet_facing: bool = False,
            is_sensitive_data: bool = False,
        ) -> dict:
            return dict(
                workspace_id=workspace_id,
                aws_account_id=aws_account_id,
                node_type=node_type,
                resource_name=resource_name,
                resource_arn=resource_arn,
                region=region,
                node_metadata=metadata or {},  # SQLAlchemy attr renamed from metadata
                finding_ids=[],
                risk_score=risk_score,
                is_internet_facing=is_internet_facing,
                is_sensitive_data=is_sensitive_data,
            )

        # ── 18 Nodes ──────────────────────────────────────────────────────

        # 1. INTERNET sentinel
        n_internet = await self._repo.create_node(**_node_kwargs(
            node_type="internet",
            resource_name="Internet / Public",
            metadata={},
        ))

        # 2. S3 PUBLIC
        n_s3_public = await self._repo.create_node(**_node_kwargs(
            node_type="s3_bucket",
            resource_name="prod-data-bucket",
            resource_arn="arn:aws:s3:::prod-data",
            metadata={"is_public": True, "is_encrypted": False, "versioning": False, "logging": False},
            risk_score=9.5,
            is_internet_facing=True,
            is_sensitive_data=True,
        ))

        # 3. S3 PRIVATE
        n_s3_private = await self._repo.create_node(**_node_kwargs(
            node_type="s3_bucket",
            resource_name="internal-logs-bucket",
            resource_arn="arn:aws:s3:::internal-logs",
            metadata={"is_public": False, "is_encrypted": True, "versioning": True, "logging": True},
            risk_score=2.0,
        ))

        # 4. IAM OVERPERMISSIONED
        n_iam_admin = await self._repo.create_node(**_node_kwargs(
            node_type="iam_role",
            resource_name="DataPipelineRole",
            resource_arn="arn:aws:iam::123456789012:role/DataPipelineRole",
            metadata={
                "permission_scope": "admin",
                "has_mfa": False,
                "cross_account": False,
                "policies": ["AmazonS3FullAccess", "AmazonRDSFullAccess"],
            },
            risk_score=8.5,
        ))

        # 5. IAM LAMBDA EXEC
        n_iam_lambda = await self._repo.create_node(**_node_kwargs(
            node_type="iam_role",
            resource_name="LambdaExecutionRole",
            resource_arn="arn:aws:iam::123456789012:role/LambdaExecutionRole",
            metadata={"permission_scope": "limited", "has_mfa": False},
            risk_score=4.0,
        ))

        # 6. IAM READ ONLY
        n_iam_read = await self._repo.create_node(**_node_kwargs(
            node_type="iam_role",
            resource_name="ReadOnlyRole",
            resource_arn="arn:aws:iam::123456789012:role/ReadOnlyRole",
            metadata={"permission_scope": "read", "has_mfa": True},
            risk_score=1.5,
        ))

        # 7. LAMBDA PROCESSOR
        n_lambda = await self._repo.create_node(**_node_kwargs(
            node_type="lambda",
            resource_name="data-processor-lambda",
            resource_arn="arn:aws:lambda:us-east-1:123456789012:function:data-processor",
            region="us-east-1",
            metadata={"runtime": "python3.11", "memory": 512, "timeout": 300},
            risk_score=6.0,
        ))

        # 8. EC2 PUBLIC
        n_ec2_public = await self._repo.create_node(**_node_kwargs(
            node_type="ec2",
            resource_name="web-server-prod",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-0abc123",
            region="us-east-1",
            metadata={"in_public_subnet": True, "has_public_ip": True, "imdsv2": False, "ami": "ami-0abc123"},
            risk_score=7.0,
            is_internet_facing=True,
        ))

        # 9. EC2 PRIVATE
        n_ec2_private = await self._repo.create_node(**_node_kwargs(
            node_type="ec2",
            resource_name="app-server-internal",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-0def456",
            region="us-east-1",
            metadata={"in_public_subnet": False, "has_public_ip": False, "imdsv2": True},
            risk_score=3.0,
        ))

        # 10. RDS PROD
        n_rds = await self._repo.create_node(**_node_kwargs(
            node_type="rds",
            resource_name="prod-postgres",
            resource_arn="arn:aws:rds:us-east-1:123456789012:db:prod-postgres",
            region="us-east-1",
            metadata={
                "is_encrypted": False,
                "multi_az": False,
                "publicly_accessible": False,
                "engine": "postgres",
                "port": 5432,
            },
            risk_score=8.0,
            is_sensitive_data=True,
        ))

        # 11. SG PERMISSIVE
        n_sg_permissive = await self._repo.create_node(**_node_kwargs(
            node_type="security_group",
            resource_name="web-sg-all-open",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:security-group/sg-0abc111",
            region="us-east-1",
            metadata={
                "allows_all_inbound": True,
                "open_ports": [22, 80, 443, 3306, 5432],
                "description": "Web tier SG - all open",
            },
            risk_score=9.0,
        ))

        # 12. SG RESTRICTED
        n_sg_restricted = await self._repo.create_node(**_node_kwargs(
            node_type="security_group",
            resource_name="db-sg-restricted",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:security-group/sg-0abc222",
            region="us-east-1",
            metadata={"allows_all_inbound": False, "open_ports": [5432]},
            risk_score=2.0,
        ))

        # 13. VPC MAIN
        n_vpc = await self._repo.create_node(**_node_kwargs(
            node_type="vpc",
            resource_name="prod-vpc",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:vpc/vpc-0abc333",
            region="us-east-1",
            metadata={"cidr": "10.0.0.0/16", "flow_logs": False},
            risk_score=3.0,
        ))

        # 14. SUBNET PUBLIC
        n_subnet_public = await self._repo.create_node(**_node_kwargs(
            node_type="subnet",
            resource_name="public-subnet-1a",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:subnet/subnet-0abc444",
            region="us-east-1",
            metadata={"is_public": True, "cidr": "10.0.1.0/24", "az": "us-east-1a"},
            is_internet_facing=True,
        ))

        # 15. SUBNET PRIVATE
        n_subnet_private = await self._repo.create_node(**_node_kwargs(
            node_type="subnet",
            resource_name="private-subnet-1a",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:subnet/subnet-0abc555",
            region="us-east-1",
            metadata={"is_public": False, "cidr": "10.0.2.0/24"},
        ))

        # 16. KMS KEY
        n_kms = await self._repo.create_node(**_node_kwargs(
            node_type="kms_key",
            resource_name="prod-kms-key",
            resource_arn="arn:aws:kms:us-east-1:123456789012:key/key-0abc666",
            region="us-east-1",
            metadata={"enabled": True, "rotation": False, "key_manager": "CUSTOMER"},
            risk_score=4.0,
        ))

        # 17. CLOUDTRAIL
        n_cloudtrail = await self._repo.create_node(**_node_kwargs(
            node_type="cloudtrail",
            resource_name="prod-cloudtrail",
            resource_arn="arn:aws:cloudtrail:us-east-1:123456789012:trail/prod-trail",
            region="us-east-1",
            metadata={"is_logging": False, "multi_region": False, "log_validation": False},
            risk_score=7.0,
        ))

        # 18. SECRETS MANAGER
        n_secrets = await self._repo.create_node(**_node_kwargs(
            node_type="secrets_manager",
            resource_name="prod-db-credentials",
            resource_arn="arn:aws:secretsmanager:us-east-1:123456789012:secret/prod-db-creds",
            region="us-east-1",
            metadata={"rotation_enabled": False, "days_since_rotation": 90},
            risk_score=6.5,
            is_sensitive_data=True,
        ))

        logger.info("seed_demo_graph.nodes_created", count=18, workspace_id=str(workspace_id))

        # ── Edge creation helper ───────────────────────────────────────────
        def _edge_kwargs(
            source_id: uuid.UUID,
            target_id: uuid.UUID,
            edge_type: str,
            is_attack_path: bool = False,
            risk_contribution: float | None = None,
            metadata: dict | None = None,
        ) -> dict:
            return dict(
                workspace_id=workspace_id,
                source_node_id=source_id,
                target_node_id=target_id,
                edge_type=edge_type,
                is_attack_path=is_attack_path,
                risk_contribution=risk_contribution,
                edge_metadata=metadata or {},  # SQLAlchemy attr renamed from metadata
            )

        # ── 20 Edges ──────────────────────────────────────────────────────

        # 1. INTERNET → S3_PUBLIC
        e1 = await self._repo.create_edge(**_edge_kwargs(
            n_internet.id, n_s3_public.id, "exposes",
            is_attack_path=True, risk_contribution=0.95,
        ))

        # 2. INTERNET → EC2_PUBLIC
        e2 = await self._repo.create_edge(**_edge_kwargs(
            n_internet.id, n_ec2_public.id, "exposes",
            is_attack_path=True, risk_contribution=0.80,
        ))

        # 3. S3_PUBLIC → IAM_OVERPERMISSIONED
        e3 = await self._repo.create_edge(**_edge_kwargs(
            n_s3_public.id, n_iam_admin.id, "has_access_to",
            is_attack_path=True, risk_contribution=0.90,
            metadata={"note": "Overpermissioned role can access this bucket"},
        ))

        # 4. IAM_OVERPERMISSIONED → LAMBDA
        e4 = await self._repo.create_edge(**_edge_kwargs(
            n_iam_admin.id, n_lambda.id, "assumes_role",
            is_attack_path=True, risk_contribution=0.85,
        ))

        # 5. IAM_OVERPERMISSIONED → RDS_PROD
        e5 = await self._repo.create_edge(**_edge_kwargs(
            n_iam_admin.id, n_rds.id, "has_access_to",
            is_attack_path=True, risk_contribution=0.88,
        ))

        # 6. IAM_OVERPERMISSIONED → SECRETS_MGR
        e6 = await self._repo.create_edge(**_edge_kwargs(
            n_iam_admin.id, n_secrets.id, "has_access_to",
            is_attack_path=True, risk_contribution=0.88,
        ))

        # 7. LAMBDA → RDS_PROD
        e7 = await self._repo.create_edge(**_edge_kwargs(
            n_lambda.id, n_rds.id, "writes_to",
            is_attack_path=True, risk_contribution=0.75,
        ))

        # 8. LAMBDA → S3_PUBLIC
        e8 = await self._repo.create_edge(**_edge_kwargs(
            n_lambda.id, n_s3_public.id, "reads_from",
            is_attack_path=False, risk_contribution=0.50,
        ))

        # 9. EC2_PUBLIC → SG_PERMISSIVE
        e9 = await self._repo.create_edge(**_edge_kwargs(
            n_ec2_public.id, n_sg_permissive.id, "is_attached_to",
            is_attack_path=True, risk_contribution=0.85,
        ))

        # 10. SG_PERMISSIVE → RDS_PROD
        e10 = await self._repo.create_edge(**_edge_kwargs(
            n_sg_permissive.id, n_rds.id, "connects_to",
            is_attack_path=True, risk_contribution=0.80,
        ))

        # 11. EC2_PUBLIC → SUBNET_PUBLIC
        e11 = await self._repo.create_edge(**_edge_kwargs(
            n_ec2_public.id, n_subnet_public.id, "is_attached_to",
            is_attack_path=False, risk_contribution=0.60,
        ))

        # 12. EC2_PRIVATE → SUBNET_PRIVATE
        e12 = await self._repo.create_edge(**_edge_kwargs(
            n_ec2_private.id, n_subnet_private.id, "is_attached_to",
            is_attack_path=False, risk_contribution=0.20,
        ))

        # 13. EC2_PRIVATE → SG_RESTRICTED
        e13 = await self._repo.create_edge(**_edge_kwargs(
            n_ec2_private.id, n_sg_restricted.id, "is_attached_to",
            is_attack_path=False, risk_contribution=0.15,
        ))

        # 14. RDS_PROD → SG_RESTRICTED
        e14 = await self._repo.create_edge(**_edge_kwargs(
            n_rds.id, n_sg_restricted.id, "is_attached_to",
            is_attack_path=False, risk_contribution=0.20,
        ))

        # 15. IAM_LAMBDA_EXEC → LAMBDA
        e15 = await self._repo.create_edge(**_edge_kwargs(
            n_iam_lambda.id, n_lambda.id, "manages",
            is_attack_path=False, risk_contribution=0.30,
        ))

        # 16. LAMBDA → SECRETS_MGR
        e16 = await self._repo.create_edge(**_edge_kwargs(
            n_lambda.id, n_secrets.id, "reads_from",
            is_attack_path=False, risk_contribution=0.45,
        ))

        # 17. VPC_MAIN → SUBNET_PUBLIC
        e17 = await self._repo.create_edge(**_edge_kwargs(
            n_vpc.id, n_subnet_public.id, "manages",
            is_attack_path=False,
        ))

        # 18. VPC_MAIN → SUBNET_PRIVATE
        e18 = await self._repo.create_edge(**_edge_kwargs(
            n_vpc.id, n_subnet_private.id, "manages",
            is_attack_path=False,
        ))

        # 19. CLOUDTRAIL → VPC_MAIN
        e19 = await self._repo.create_edge(**_edge_kwargs(
            n_cloudtrail.id, n_vpc.id, "manages",
            is_attack_path=False,
        ))

        # 20. S3_PRIVATE → KMS_KEY
        e20 = await self._repo.create_edge(**_edge_kwargs(
            n_s3_private.id, n_kms.id, "stores_data_in",
            is_attack_path=False,
        ))

        logger.info("seed_demo_graph.edges_created", count=20, workspace_id=str(workspace_id))

        # ── Attack Path 1: CRITICAL — Internet → S3 → IAM → RDS ──────────
        ap1 = await self._repo.create_attack_path(
            workspace_id=workspace_id,
            name="Internet to Production Database via Public S3",
            description=(
                "Attacker exploits publicly accessible S3 bucket to discover "
                "overpermissioned IAM role, then leverages that role to access "
                "the production RDS database directly."
            ),
            severity="critical",
            node_path=[
                str(n_internet.id),
                str(n_s3_public.id),
                str(n_iam_admin.id),
                str(n_rds.id),
            ],
            edge_path=[str(e1.id), str(e3.id), str(e5.id)],
            toxic_combo_tags=["public_s3", "no_encryption", "overpermissioned_iam", "unencrypted_rds"],
            blast_radius=5,
            entry_node_id=n_internet.id,
            target_node_id=n_rds.id,
            entry_description="Publicly accessible unencrypted S3 bucket",
            target_description="Unencrypted production PostgreSQL database",
            is_active=True,
            related_finding_ids=[],
        )

        # ── Attack Path 2: HIGH — Internet → EC2 → SG → RDS ──────────────
        ap2 = await self._repo.create_attack_path(
            workspace_id=workspace_id,
            name="Internet-Facing EC2 to RDS via Permissive Security Group",
            description=(
                "Overly permissive security group allows internet-accessible "
                "EC2 instance to directly reach production RDS on port 5432."
            ),
            severity="high",
            node_path=[
                str(n_internet.id),
                str(n_ec2_public.id),
                str(n_sg_permissive.id),
                str(n_rds.id),
            ],
            edge_path=[str(e2.id), str(e9.id), str(e10.id)],
            toxic_combo_tags=["public_ec2", "open_security_group", "unencrypted_rds"],
            blast_radius=3,
            entry_node_id=n_internet.id,
            target_node_id=n_rds.id,
            entry_description="Internet-facing EC2 instance in public subnet",
            target_description="Production RDS database reachable via permissive security group",
            is_active=True,
            related_finding_ids=[],
        )

        logger.info(
            "seed_demo_graph.complete",
            workspace_id=str(workspace_id),
            nodes=18,
            edges=20,
            attack_paths=2,
        )

        return {
            "nodes_created": 18,
            "edges_created": 20,
            "attack_paths_created": 2,
            "attack_path_ids": [str(ap1.id), str(ap2.id)],
            "workspace_id": str(workspace_id),
        }
