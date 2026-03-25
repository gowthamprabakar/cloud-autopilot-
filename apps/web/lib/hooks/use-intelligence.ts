import useSWR from "swr"
import { apiFetcher } from "@/lib/api-client"
import type { FindingIntelligence, WorkspaceIntelligenceSummary, IntelligenceHealth } from "@/lib/types"

export function useFindingIntelligence(findingId: string | null) {
  return useSWR<FindingIntelligence>(
    findingId ? `/api/v1/intelligence/findings/${findingId}` : null,
    apiFetcher
  )
}

export function useIntelligenceSummary() {
  return useSWR<WorkspaceIntelligenceSummary>("/api/v1/intelligence/workspace/summary", apiFetcher)
}

export function useIntelligenceHealth() {
  return useSWR<IntelligenceHealth>("/api/v1/intelligence/health", apiFetcher, { refreshInterval: 30000 })
}
