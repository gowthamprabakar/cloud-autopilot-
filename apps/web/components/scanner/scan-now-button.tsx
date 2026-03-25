"use client"

import { useState, useEffect } from "react"
import { RefreshCw, Loader2 } from "lucide-react"
import { triggerScan, useScanStatus } from "@/lib/hooks/use-scanner"

interface ScanNowButtonProps {
  awsAccountId?: string
  variant?: "default" | "outline" | "ghost"
  size?: "default" | "sm" | "lg" | "icon"
  label?: string
}

export function ScanNowButton({
  awsAccountId,
  label = "Scan Now",
}: ScanNowButtonProps) {
  const { isRunning, scanJob: latestJob, mutate: refresh } = useScanStatus()
  const [isTriggering, setIsTriggering] = useState(false)
  const [prevStatus, setPrevStatus] = useState<string | null>(null)
  const [statusMsg, setStatusMsg] = useState<string | null>(null)

  useEffect(() => {
    if (!latestJob) return
    if (prevStatus === "running" && latestJob.status === "completed") {
      setStatusMsg(
        `Scan complete — ${latestJob.findings_added} new finding${latestJob.findings_added !== 1 ? "s" : ""} added`
      )
    } else if (prevStatus === "running" && latestJob.status === "failed") {
      setStatusMsg(`Scan failed: ${latestJob.error_message || "unknown error"}`)
    } else if (prevStatus === "running" && latestJob.status === "partial") {
      setStatusMsg(
        `Scan partial — ${latestJob.findings_added} new findings (${latestJob.sources_failed.join(", ")} unavailable)`
      )
    }
    setPrevStatus(latestJob.status)
  }, [latestJob?.status])

  const handleClick = async () => {
    if (isRunning || isTriggering) return
    setIsTriggering(true)
    setStatusMsg(null)
    try {
      const result = await triggerScan(awsAccountId)
      if (result.status === "already_running") {
        setStatusMsg("A scan is already in progress")
      } else {
        setStatusMsg("Scan started — checking AWS for new findings…")
        setPrevStatus("running")
      }
      refresh()
    } catch (err: unknown) {
      setStatusMsg(err instanceof Error ? err.message : "Failed to start scan")
    } finally {
      setIsTriggering(false)
    }
  }

  const busy = isRunning || isTriggering

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={handleClick}
        disabled={busy}
        className="inline-flex items-center gap-1.5 rounded-md border border-slate-600 bg-slate-800 px-3 py-1.5 text-sm font-medium text-slate-200 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
      >
        {busy ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <RefreshCw className="h-3.5 w-3.5" />
        )}
        {busy ? "Scanning…" : label}
      </button>
      {statusMsg && (
        <span className="text-xs text-slate-400">{statusMsg}</span>
      )}
    </div>
  )
}
