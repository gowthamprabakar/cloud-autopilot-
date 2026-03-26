"use client";
import useSWR from "swr";
import { apiFetcher } from "@/lib/api-client";

export interface CSPMPosture {
  total_rules: number;
  total_passed: number;
  total_failed: number;
  posture_score: number;
  categories: Record<string, {
    rules: number;
    passed: number;
    failed: number;
    pass_rate: number;
    findings: Array<{ id: string; title: string; severity: string; resource_arn: string }>;
  }>;
  frameworks: Record<string, { total_controls: number; passed: number; failed: number; score: number }>;
  total_findings: number;
  open_findings: number;
}

export interface WorkloadAssessment {
  total_workloads: number;
  vm_count: number;
  container_count: number;
  serverless_count: number;
  critical_cves: number;
  workloads: Array<{ type: string; name: string; cve_count: number; risk_score: number }>;
}

export function useCSPMPosture() {
  const { data, error, isLoading } = useSWR<CSPMPosture>(
    "/api/v1/modules/cspm/posture", apiFetcher, { revalidateOnFocus: false }
  );
  return { posture: data ?? null, isLoading, error };
}

export function useWorkloadAssessment() {
  const { data, error, isLoading } = useSWR<WorkloadAssessment>(
    "/api/v1/modules/cwpp/workloads", apiFetcher, { revalidateOnFocus: false }
  );
  return { workloads: data ?? null, isLoading, error };
}
