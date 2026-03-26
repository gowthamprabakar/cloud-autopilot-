"use client";
import useSWR from "swr";
import { apiFetcher } from "@/lib/api-client";

export interface GraphSummary {
  total_nodes: number;
  total_edges: number;
  nodes_by_type: Record<string, number>;
  edges_by_type: Record<string, number>;
}

export interface AttackPathResult {
  nodes: Array<{ arn: string; type: string; name: string; risk_score: number }>;
  edges: Array<{ type: string; from: string; to: string }>;
  depth: number;
}

export interface BlastRadiusResult {
  origin: string;
  reachable_count: number;
  reachable_nodes: Array<{ arn: string; type: string; name: string }>;
}

export interface ToxicCombination {
  resource_arn: string;
  resource_type: string;
  resource_name: string;
  findings: Array<{ title: string; severity: string; cve_id: string | null }>;
  finding_count: number;
}

export function useGraphSummary() {
  const { data, error, isLoading } = useSWR<GraphSummary>("/api/v1/graph/summary", apiFetcher, { revalidateOnFocus: false });
  return { summary: data ?? null, isLoading, error };
}

export function useToxicCombinations() {
  const { data, error, isLoading } = useSWR<ToxicCombination[]>("/api/v1/graph/toxic-combinations", apiFetcher, { revalidateOnFocus: false });
  return { combinations: data ?? [], isLoading, error };
}
