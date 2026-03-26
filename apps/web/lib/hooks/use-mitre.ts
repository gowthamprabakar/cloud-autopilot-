"use client";
import useSWR from "swr";
import { apiFetcher } from "@/lib/api-client";

export interface TechniqueCoverage {
  technique_id: string;
  name: string;
  tactic: string;
  covered: boolean;
  finding_count: number;
}

export interface TacticHeatmap {
  tactics: Record<string, {
    total_techniques: number;
    covered: number;
    coverage_pct: number;
    techniques: TechniqueCoverage[];
  }>;
}

export interface CoverageResult {
  total_techniques: number;
  covered: number;
  uncovered: number;
  coverage_pct: number;
  techniques: Record<string, TechniqueCoverage>;
}

export function useMITRECoverage() {
  const { data, error, isLoading } = useSWR<CoverageResult>(
    "/api/v1/mitre/coverage", apiFetcher, { revalidateOnFocus: false }
  );
  return { coverage: data ?? null, isLoading, error };
}

export function useMITREHeatmap() {
  const { data, error, isLoading } = useSWR<TacticHeatmap>(
    "/api/v1/mitre/heatmap", apiFetcher, { revalidateOnFocus: false }
  );
  return { heatmap: data ?? null, isLoading, error };
}
