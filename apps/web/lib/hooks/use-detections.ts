"use client";
import useSWR from "swr";
import { apiFetcher } from "@/lib/api-client";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface DetectionSummary {
  total_alerts: number;
  open_alerts: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  avg_confidence: number;
  top_tactic: string;
  rules_fired: number;
  by_tactic: Record<string, number>;
  by_rule: Record<string, number>;
}

export interface DetectionAlert {
  id: string;
  rule_id: string;
  title: string;
  description: string;
  severity: "critical" | "high" | "medium";
  confidence: number;
  tactic: string;
  technique: string;
  risk_score: number;
  status: string;
  affected_resources: Array<{ arn: string; type: string; region: string }>;
  finding_ids: string[];
  detected_at: string;
  evidence: string;
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useDetectionSummary() {
  const { data, error, isLoading, mutate } = useSWR<DetectionSummary>(
    "/api/v1/detections/summary",
    apiFetcher,
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );
  return { summary: data ?? null, isLoading, error, mutate };
}

export function useDetectionAlerts() {
  const { data, error, isLoading } = useSWR<DetectionAlert[]>(
    "/api/v1/detections/alerts",
    apiFetcher,
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );
  return { alerts: data ?? [], isLoading, error };
}
