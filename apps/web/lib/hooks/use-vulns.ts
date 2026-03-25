"use client";
import useSWR from "swr";
import { apiFetcher } from "@/lib/api-client";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface VulnSummary {
  total_cves: number;
  active_cves: number;
  kev_count: number;
  critical_epss_count: number;
  avg_epss: number;
  max_epss: number;
  severity_breakdown: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  epss_distribution: {
    "0.9+": number;
    "0.5-0.9": number;
    "0.1-0.5": number;
    "<0.1": number;
  };
}

export interface VulnResource {
  resource_arn: string;
  resource_type: string;
  region: string;
  severity: string;
  status: string;
  finding_title: string;
  finding_id: string;
}

export interface VulnItem {
  cve_id: string;
  severity: string;
  epss_score: number | null;
  in_kev: boolean;
  risk_tier: "imminent" | "high" | "elevated" | "moderate";
  open_count: number;
  total_count: number;
  affected_count: number;
  resources: VulnResource[];
  cvss_score: number;
  first_seen: string | null;
  last_seen: string | null;
  description: string;
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useVulnSummary() {
  const { data, error, isLoading, mutate } = useSWR<VulnSummary>(
    "/api/v1/vulns/summary",
    apiFetcher,
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );
  return { summary: data ?? null, isLoading, error, mutate };
}

export function useVulnInventory() {
  const { data, error, isLoading } = useSWR<VulnItem[]>(
    "/api/v1/vulns/inventory",
    apiFetcher,
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );
  return { items: data ?? [], isLoading, error };
}
