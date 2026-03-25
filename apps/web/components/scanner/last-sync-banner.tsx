"use client"

import { RefreshCw, Loader2, CheckCircle2, AlertTriangle, XCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import { ScanNowButton } from "@/components/scanner/scan-now-button"
import { useScanStatus } from "@/lib/hooks/use-scanner"

export function LastSyncBanner({ className }: { className?: string }) {
  const { isRunning, message, scanJob: latestJob } = useScanStatus()

  if (!latestJob && !isRunning) return null

  const statusColor = isRunning
    ? "bg-blue-50 border-blue-200 text-blue-700"
    : latestJob?.status === "completed"
    ? "bg-emerald-50 border-emerald-200 text-emerald-700"
    : latestJob?.status === "failed"
    ? "bg-red-50 border-red-200 text-red-700"
    : latestJob?.status === "partial"
    ? "bg-amber-50 border-amber-200 text-amber-700"
    : "bg-slate-50 border-slate-200 text-slate-600"

  const Icon = isRunning
    ? Loader2
    : latestJob?.status === "completed"
    ? CheckCircle2
    : latestJob?.status === "failed"
    ? XCircle
    : latestJob?.status === "partial"
    ? AlertTriangle
    : RefreshCw

  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-lg border px-4 py-2.5 text-sm",
        statusColor,
        className
      )}
    >
      <Icon
        className={cn("h-4 w-4 shrink-0", isRunning && "animate-spin")}
      />

      <span className="flex-1 font-medium">{message}</span>

      {latestJob && !isRunning && (
        <span className="text-xs opacity-70">
          {latestJob.findings_total} processed · {latestJob.sources_scanned.length} sources
          {latestJob.duration_seconds
            ? ` · ${latestJob.duration_seconds.toFixed(1)}s`
            : ""}
        </span>
      )}

      <ScanNowButton size="sm" variant="ghost" label="Sync Now" />
    </div>
  )
}
