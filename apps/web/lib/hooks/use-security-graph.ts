import useSWR from "swr"
import { apiFetcher } from "@/lib/api-client"
import type { SecurityGraphResponse, AttackPath } from "@/lib/types"

export function useSecurityGraph() {
  return useSWR<SecurityGraphResponse>("/api/v1/security-graph", apiFetcher)
}

export function useAttackPaths() {
  return useSWR<AttackPath[]>("/api/v1/security-graph/attack-paths", apiFetcher)
}
