"use client";
import useSWR from "swr";
import { apiFetcher } from "@/lib/api-client";
import type { FindingComment } from "@/lib/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function useFindingComments(findingId: string) {
  const { data, error, isLoading, mutate } = useSWR<FindingComment[]>(
    findingId ? `/api/v1/findings/${findingId}/comments` : null,
    apiFetcher
  );
  return { comments: data ?? [], error, isLoading, mutate };
}

export async function addComment(findingId: string, body: string): Promise<FindingComment> {
  const res = await fetch(`${API}/api/v1/findings/${findingId}/comments`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ body }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function deleteComment(findingId: string, commentId: string): Promise<void> {
  const res = await fetch(`${API}/api/v1/findings/${findingId}/comments/${commentId}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!res.ok) throw new Error(await res.text());
}
