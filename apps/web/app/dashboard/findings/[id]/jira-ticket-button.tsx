"use client"
import { useState, useEffect } from "react"
import { createJiraTicket, getJiraTicket } from "@/lib/hooks/use-jira"
import type { JiraTicket } from "@/lib/types"

interface JiraTicketButtonProps {
  findingId: string
}

export function JiraTicketButton({ findingId }: JiraTicketButtonProps) {
  const [ticket, setTicket] = useState<JiraTicket | null>(null)
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Check for existing ticket on mount
  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      try {
        const existing = await getJiraTicket(findingId)
        if (!cancelled) setTicket(existing)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [findingId])

  async function handleCreate() {
    setCreating(true)
    setError(null)
    try {
      const result = await createJiraTicket(findingId)
      if (result.success && result.jira_key && result.jira_url) {
        setTicket({
          id: "",
          finding_id: findingId,
          workspace_id: "",
          jira_key: result.jira_key,
          jira_url: result.jira_url,
          created_at: new Date().toISOString(),
        })
      } else {
        setError(result.error ?? "Failed to create Jira ticket.")
      }
    } catch {
      setError("An unexpected error occurred.")
    } finally {
      setCreating(false)
    }
  }

  if (loading) {
    return (
      <div className="h-8 w-36 animate-pulse rounded-lg bg-slate-100" />
    )
  }

  if (ticket) {
    return (
      <a
        href={ticket.jira_url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1.5 rounded-lg border border-blue-300 bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-100 transition-colors"
      >
        View in Jira → {ticket.jira_key}
      </a>
    )
  }

  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        onClick={handleCreate}
        disabled={creating}
        className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 transition-colors"
      >
        {creating ? "Creating…" : "Create Jira Ticket"}
      </button>
      {error && <span className="text-xs text-red-600">{error}</span>}
    </div>
  )
}
