"use client";
import useSWR from "swr";
import { apiFetcher, apiClient } from "@/lib/api-client";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface SimulationRun {
  id: string;
  domain: string;
  status: "pending" | "running" | "completed" | "failed";
  agent_count: number;
  message_count: number;
  solution_count: number;
  gates_passed: number;
  gates_total: number;
  confidence_score: number;
  total_tokens_used: number;
  total_cost_usd: number;
  duration_seconds: number | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface SwarmAgent {
  id: string;
  agent_id: string;
  name: string;
  role: string;
  status: "idle" | "running" | "done" | "error" | "spawning";
  progress: number;
  autonomy_level: number;
  spawn_authority: boolean;
  output: string | null;
  working_memory: Record<string, any> | null;
  episodic_memory: string[] | null;
  goal_stack: string[] | null;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
}

export interface CommMessage {
  id: string;
  from_agent_id: string;
  to_agent_id: string;
  message_type: "info" | "solution" | "alert" | "spawn" | "wiz";
  body: string;
  sequence_number: number;
  created_at: string;
}

export interface ValidationGate {
  gate_number: number;
  name: string;
  state: "pending" | "running" | "pass" | "fail" | "partial";
  score: number;
  evidence: string | null;
  is_double_weight: boolean;
  coverage: "wiz" | "swarm" | "both";
}

export interface SimulationDetail extends SimulationRun {
  agents: SwarmAgent[];
  messages: CommMessage[];
  gates: ValidationGate[];
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useSimulations() {
  const { data, error, isLoading, mutate } = useSWR<SimulationRun[]>(
    "/api/v1/simulations",
    apiFetcher,
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );
  return { simulations: data ?? [], isLoading, error, mutate };
}

export function useSimulationDetail(runId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<SimulationDetail>(
    runId ? `/api/v1/simulations/${runId}` : null,
    apiFetcher,
    {
      revalidateOnFocus: false,
      shouldRetryOnError: false,
      refreshInterval: (latestData) =>
        latestData?.status === "running" ? 2000 : 0,
    }
  );
  return { detail: data ?? null, isLoading, error, mutate };
}

export async function launchSimulation(
  domain: string,
  config?: Record<string, unknown>
) {
  return apiClient.post<SimulationRun>("/api/v1/simulations", {
    domain,
    ...config,
  });
}

export async function deleteSimulation(runId: string) {
  return apiClient.delete<void>(`/api/v1/simulations/${runId}`);
}
