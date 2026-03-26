"use client";
import useSWR from "swr";
import { apiFetcher, apiClient } from "@/lib/api-client";

export interface MemorySummary {
  total_memories: number;
  by_type: Record<string, number>;
  avg_relevance: number;
  oldest: string | null;
  newest: string | null;
}

export interface MemoryEntry {
  id: string;
  agent_id: string;
  memory_type: "working" | "episodic" | "semantic" | "procedural";
  key: string;
  value: any;
  relevance_score: number;
  access_count: number;
  last_accessed_at: string | null;
  created_at: string;
}

export function useAgentMemory(agentId: string) {
  const { data, error, isLoading, mutate } = useSWR<MemorySummary>(
    agentId ? `/api/v1/memory/${agentId}` : null, apiFetcher, { revalidateOnFocus: false }
  );
  return { summary: data ?? null, isLoading, error, mutate };
}

export function useAgentMemoryRecall(agentId: string, type?: string) {
  const url = agentId ? `/api/v1/memory/${agentId}/recall${type ? `?type=${type}` : ''}` : null;
  const { data, error, isLoading } = useSWR<MemoryEntry[]>(url, apiFetcher, { revalidateOnFocus: false });
  return { memories: data ?? [], isLoading, error };
}

export async function triggerLearn(runId: string) {
  return apiClient.post(`/api/v1/memory/learn/${runId}`, {});
}
