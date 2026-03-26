"use client";
import useSWR from "swr";
import { apiFetcher } from "@/lib/api-client";

export interface ModuleEndpointData {
  [key: string]: any;
}

export function useModuleEndpoint<T = ModuleEndpointData>(
  moduleSlug: string,
  endpoint: string
) {
  const url = `/api/v1/modules/${moduleSlug}/${endpoint}`;
  const { data, error, isLoading, mutate } = useSWR<T>(
    url,
    apiFetcher,
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );
  return { data: data ?? null, isLoading, error, mutate };
}
