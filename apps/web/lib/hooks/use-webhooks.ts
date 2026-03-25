"use client";
import useSWR from "swr";
import { apiFetcher } from "@/lib/api-client";
import type { WebhookDestination, WebhookCreate, WebhookCreatedResponse } from "@/lib/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function useWebhooks() {
  const { data, error, isLoading, mutate } = useSWR<WebhookDestination[]>(
    "/api/v1/webhooks",
    apiFetcher
  );
  return { webhooks: data ?? [], error, isLoading, mutate };
}

export async function createWebhook(req: WebhookCreate): Promise<WebhookCreatedResponse> {
  const res = await fetch(`${API}/api/v1/webhooks`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function deleteWebhook(webhookId: string): Promise<void> {
  const res = await fetch(`${API}/api/v1/webhooks/${webhookId}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!res.ok) throw new Error(await res.text());
}

export async function testWebhook(webhookId: string): Promise<{ delivered: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/webhooks/${webhookId}/test`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
