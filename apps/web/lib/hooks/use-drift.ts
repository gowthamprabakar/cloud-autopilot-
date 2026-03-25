"use client";
import useSWR from "swr";
import { apiFetcher } from "@/lib/api-client";

export interface DriftSummary {
  recurrence_count: number;
  drift_signal_count: number;
  root_cause_clusters: number;
  total_recurred_findings: number;
  total_drifted_resources: number;
  top_cluster_pattern: string;
  top_cluster_size: number;
}

export interface Recurrence {
  fingerprint: string;
  finding_id: string;
  title: string;
  severity: string;
  resource_arn: string;
  status: string;
  first_resolved_at: string | null;
  reopened_at: string | null;
  occurrences: number;
}

export interface DriftSignal {
  resource_arn: string;
  resource_type: string;
  drift_type: string;
  severities: string[];
  finding_count: number;
  worst_severity: string;
  worst_title: string;
  region: string;
}

export interface RootCauseCluster {
  cluster_id: string;
  root_cause_pattern: string;
  resource_type: string;
  finding_count: number;
  severity_distribution: Record<string, number>;
  affected_resources: string[];
  sample_title: string;
  sample_finding_id: string;
}

export function useDriftSummary() {
  const { data, error, isLoading } = useSWR<DriftSummary>(
    "/api/v1/drift/summary", apiFetcher,
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );
  return { summary: data ?? null, isLoading, error };
}

export function useRecurrences() {
  const { data, error, isLoading } = useSWR<Recurrence[]>(
    "/api/v1/drift/recurrences", apiFetcher,
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );
  return { recurrences: data ?? [], isLoading, error };
}

export function useDriftSignals() {
  const { data, error, isLoading } = useSWR<DriftSignal[]>(
    "/api/v1/drift/signals", apiFetcher,
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );
  return { signals: data ?? [], isLoading, error };
}

export function useRootCauseClusters() {
  const { data, error, isLoading } = useSWR<RootCauseCluster[]>(
    "/api/v1/drift/clusters", apiFetcher,
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );
  return { clusters: data ?? [], isLoading, error };
}
