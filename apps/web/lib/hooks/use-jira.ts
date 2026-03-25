import type { JiraConnectionTest, JiraTicket } from "@/lib/types"

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export async function testJiraConnection(): Promise<JiraConnectionTest> {
  const res = await fetch(`${API}/api/v1/jira/test`, {
    method: "POST",
    credentials: "include",
  })
  if (!res.ok) {
    const text = await res.text()
    return { ok: false, message: text || "Connection failed" }
  }
  return res.json() as Promise<JiraConnectionTest>
}

export async function createJiraTicket(findingId: string): Promise<{
  success: boolean
  jira_key?: string
  jira_url?: string
  error?: string
}> {
  const res = await fetch(`${API}/api/v1/jira/tickets`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ finding_id: findingId }),
  })
  if (!res.ok) {
    const text = await res.text()
    return { success: false, error: text || "Failed to create ticket" }
  }
  const ticket = (await res.json()) as JiraTicket
  return { success: true, jira_key: ticket.jira_key, jira_url: ticket.jira_url }
}

export async function getJiraTicket(findingId: string): Promise<JiraTicket | null> {
  const res = await fetch(`${API}/api/v1/jira/tickets/finding/${findingId}`, {
    credentials: "include",
  })
  if (!res.ok) return null
  return res.json() as Promise<JiraTicket>
}
