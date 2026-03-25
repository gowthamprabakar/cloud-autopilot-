"use client";
import useSWR from "swr";
import { apiFetcher } from "@/lib/api-client";
import type { FindingAssignment, AssignFindingRequest } from "@/lib/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Hook for a single finding's assignment
export function useFindingAssignment(findingId: string) {
  const { data, error, isLoading, mutate } = useSWR<FindingAssignment | null>(
    findingId ? `/api/v1/findings/${findingId}/assignment` : null,
    async (url: string) => {
      const res = await fetch(`${API}${url}`, { credentials: "include" });
      if (res.status === 404) return null;
      if (!res.ok) throw new Error(await res.text());
      return res.json() as Promise<FindingAssignment>;
    }
  );
  return { assignment: data ?? null, error, isLoading, mutate };
}

// Hook for "My Assignments"
export function useMyAssignments() {
  const { data, error, isLoading, mutate } = useSWR<FindingAssignment[]>(
    "/api/v1/findings/assigned-to-me",
    apiFetcher
  );
  return { assignments: data ?? [], error, isLoading, mutate };
}

export async function assignFinding(
  findingId: string,
  req: AssignFindingRequest
): Promise<FindingAssignment> {
  const res = await fetch(`${API}/api/v1/findings/${findingId}/assign`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<FindingAssignment>;
}

export async function unassignFinding(findingId: string): Promise<void> {
  const res = await fetch(`${API}/api/v1/findings/${findingId}/assignment`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!res.ok && res.status !== 404) throw new Error(await res.text());
}
