"use client";
import useSWR from "swr";
import { apiFetcher } from "@/lib/api-client";

export interface AttackPathNode {
  id: string;
  name: string;
  type: string;
  resource_arn: string;
  region: string;
  risk_score: number;
  is_internet_facing: boolean;
}

export interface AttackPathEdge {
  id: string;
  source_id: string;
  target_id: string;
  edge_type: string;
  risk_contribution: number;
  is_attack_path: boolean;
}

export interface AttackPath {
  id: string;
  nodes: AttackPathNode[];
  edges: AttackPathEdge[];
  total_risk: number;
  length: number;
  source_name: string;
  target_name: string;
  severity: string;
}

export interface AttackPathSummary {
  total_paths: number;
  critical_paths: number;
  avg_risk: number;
  max_chain_length: number;
  most_targeted_node: string;
  paths_by_severity: Record<string, number>;
}

export interface BlastRadius {
  origin: AttackPathNode;
  reachable_nodes: AttackPathNode[];
  edges: AttackPathEdge[];
  total_reachable: number;
  max_depth: number;
}

export function useAttackPathSummary() {
  const { data, error, isLoading } = useSWR<AttackPathSummary>(
    "/api/v1/attack-paths/summary",
    apiFetcher,
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );
  return { summary: data ?? null, isLoading, error };
}

export function useAttackPaths() {
  const { data, error, isLoading } = useSWR<AttackPath[]>(
    "/api/v1/attack-paths",
    apiFetcher,
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );
  return { paths: data ?? [], isLoading, error };
}

export function useBlastRadius(nodeId: string | null) {
  const { data, error, isLoading } = useSWR<BlastRadius>(
    nodeId ? `/api/v1/attack-paths/blast-radius/${nodeId}` : null,
    apiFetcher,
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );
  return { blastRadius: data ?? null, isLoading, error };
}
