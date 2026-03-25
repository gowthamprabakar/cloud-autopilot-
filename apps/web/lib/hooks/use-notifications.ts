"use client";
import useSWR from "swr";
import { apiFetcher } from "@/lib/api-client";
import type { NotificationListResponse } from "@/lib/types";

export function useNotifications(unreadOnly = false) {
  const key = `/api/v1/notifications${unreadOnly ? "?unread_only=true" : ""}`;
  const { data, error, isLoading, mutate } = useSWR<NotificationListResponse>(
    key,
    apiFetcher,
    { refreshInterval: 30_000 } // poll every 30s
  );
  return { data, error, isLoading, mutate };
}

export async function markNotificationRead(id: string): Promise<void> {
  await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/notifications/${id}/read`, {
    method: "PATCH",
    credentials: "include",
  });
}

export async function markAllNotificationsRead(): Promise<void> {
  await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/notifications/read-all`, {
    method: "POST",
    credentials: "include",
  });
}
