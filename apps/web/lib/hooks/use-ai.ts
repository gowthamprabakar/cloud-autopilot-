/**
 * AI Safe Layer hooks.
 *
 * Rules:
 * - Never store or compute severity/risk_score from AI responses.
 * - All mutation hooks go through the API; no local state overrides.
 */

import useSWR from "swr";
import { apiClient, authHeaders } from "@/lib/api-client";
import type {
  AiFeedbackRequest,
  AiFeedbackResponse,
  AiInsight,
  GenerateInsightRequest,
} from "@/lib/types";

// ── Fetcher ────────────────────────────────────────────────────────────────

async function fetcher<T>(url: string): Promise<T> {
  const res = await fetch(url, {
    headers: authHeaders() as HeadersInit,
    credentials: "include",
  });
  if (res.status === 204 || res.headers.get("content-length") === "0") {
    return null as T;
  }
  const data = await res.json();
  if (!res.ok) throw data;
  return data;
}

// ── Hooks ──────────────────────────────────────────────────────────────────

/**
 * Get the latest completed AI insight for a finding.
 * Returns null when no insight has been generated yet.
 */
export function useAiInsight(findingId: string | undefined) {
  const { data, error, isLoading, mutate } = useSWR<AiInsight | null>(
    findingId
      ? `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/v1/ai/findings/${findingId}/insights/latest`
      : null,
    fetcher,
    { revalidateOnFocus: false }
  );

  return {
    insight: data ?? null,
    isLoading,
    error,
    mutate,
  };
}

/**
 * Generate (or return cached) an AI insight for a finding.
 * Idempotent: repeated calls with same context return cached insight.
 */
export async function generateInsight(
  findingId: string,
  req: GenerateInsightRequest = { prompt_template_id: "finding_summary_v1" }
): Promise<AiInsight> {
  return apiClient.post<AiInsight>(
    `/api/v1/ai/findings/${findingId}/insights`,
    req,
    { headers: authHeaders() }
  );
}

/**
 * Submit human feedback on an AI insight.
 */
export async function submitAiFeedback(
  insightId: string,
  req: AiFeedbackRequest
): Promise<AiFeedbackResponse> {
  return apiClient.post<AiFeedbackResponse>(
    `/api/v1/ai/insights/${insightId}/feedback`,
    req,
    { headers: authHeaders() }
  );
}
