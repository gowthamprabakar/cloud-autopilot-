"use client";
import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useFinding } from "@/lib/hooks/use-findings";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { apiClient, authHeaders } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { FindingStatus } from "@/lib/types";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { AiInsightCard } from "@/components/ai/ai-insight-card";
import { TriagePanel } from "@/components/agents/triage-panel";
import { CommentsSection } from "./comments-section";
import { AssignmentWidget } from "./assignment-widget";
import { JiraTicketButton } from "./jira-ticket-button";
import { useAuth } from "@/lib/hooks/use-auth";
import dynamic from "next/dynamic";

const SecurityIntelligencePanel = dynamic(
  () => import("@/components/intelligence/security-intelligence-panel"),
  { ssr: false }
);

const STATUS_TRANSITIONS: FindingStatus[] = ["open", "in_progress", "resolved", "accepted", "suppressed"];

export default function FindingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const { finding, isLoading, error, mutate } = useFinding(id);
  const { user } = useAuth();
  const [updating, setUpdating] = useState(false);
  const [showSuppressModal, setShowSuppressModal] = useState(false);
  const [suppressReason, setSuppressReason] = useState("");
  const [suppressing, setSuppressing] = useState(false);
  const [generatingIntel, setGeneratingIntel] = useState(false);

  async function handleGenerateIntelligence() {
    setGeneratingIntel(true);
    try {
      await apiClient.post(`/api/v1/intelligence/findings/${id}`, {});
    } finally {
      setGeneratingIntel(false);
    }
  }

  async function handleStatusChange(newStatus: FindingStatus) {
    if (!finding) return;
    setUpdating(true);
    try {
      await apiClient.patch(`/api/v1/findings/${id}`, { status: newStatus }, { headers: authHeaders() });
      await mutate();
    } finally {
      setUpdating(false);
    }
  }

  async function handleSuppressSubmit() {
    if (!suppressReason.trim()) return;
    setSuppressing(true);
    try {
      const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      await fetch(`${API}/api/v1/suppression-rules`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: `Suppress: ${finding?.title.slice(0, 80)}`,
          reason: suppressReason,
          match_title_contains: finding?.title,
        }),
      });
      // Apply rules and refresh
      await fetch(`${API}/api/v1/suppression-rules/apply`, { method: "POST", credentials: "include" });
      setShowSuppressModal(false);
      setSuppressReason("");
      router.refresh();
    } catch {
      // error is surfaced via the modal remaining open
    } finally {
      setSuppressing(false);
    }
  }

  if (isLoading) return <div className="flex justify-center p-12"><Spinner className="h-6 w-6" /></div>;
  if (error || !finding) return (
    <div className="text-center p-12">
      <p className="text-sm text-red-500">Finding not found.</p>
      <Link href="/dashboard/findings" className="mt-2 text-sm text-blue-600 hover:underline">Back to findings</Link>
    </div>
  );

  return (
    <div className="max-w-4xl space-y-6">
      {/* Back */}
      <Link href="/dashboard/findings" className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to Findings
      </Link>

      {/* Header card */}
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <div className="flex items-start justify-between gap-3 mb-4">
          <div className="flex items-start gap-3 flex-wrap">
            <Badge variant={finding.severity} className="mt-0.5">{finding.severity}</Badge>
            <Badge variant={finding.status as any}>{finding.status.replace("_", " ")}</Badge>
            {finding.risk_score !== null && finding.risk_score !== undefined && (
              <div className={cn(
                "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold",
                finding.risk_score >= 8 ? "bg-red-100 text-red-700" :
                finding.risk_score >= 6 ? "bg-orange-100 text-orange-700" :
                finding.risk_score >= 4 ? "bg-amber-100 text-amber-700" :
                finding.risk_score >= 2 ? "bg-yellow-100 text-yellow-700" :
                "bg-slate-100 text-slate-600"
              )}>
                <span>Risk</span>
                <span>{finding.risk_score.toFixed(1)}</span>
              </div>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={handleGenerateIntelligence}
              disabled={generatingIntel}
              className="px-3 py-1.5 text-sm rounded-lg border border-blue-300 bg-blue-50 text-blue-700 hover:bg-blue-100 disabled:opacity-50 transition-colors"
            >
              {generatingIntel ? "Generating..." : "Generate Intelligence"}
            </button>
            <JiraTicketButton findingId={id} />
            {(user?.role === "admin" || user?.role === "super_admin") && (
              <button
                onClick={() => setShowSuppressModal(true)}
                className="px-3 py-1.5 text-sm rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-100 transition-colors"
              >
                Suppress
              </button>
            )}
          </div>
        </div>
        <h1 className="text-lg font-bold text-slate-900">{finding.title}</h1>
        {finding.description && (
          <p className="mt-2 text-sm text-slate-600 leading-relaxed">{finding.description}</p>
        )}
      </div>

      {/* Details grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Resource */}
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Resource</h3>
          <dl className="space-y-2 text-sm">
            {finding.resource_arn && (
              <div>
                <dt className="text-slate-400 text-xs">ARN</dt>
                <dd className="font-mono text-xs text-slate-700 break-all">{finding.resource_arn}</dd>
              </div>
            )}
            {finding.resource_type && (
              <div>
                <dt className="text-slate-400 text-xs">Type</dt>
                <dd className="text-slate-700">{finding.resource_type}</dd>
              </div>
            )}
            {finding.region && (
              <div>
                <dt className="text-slate-400 text-xs">Region</dt>
                <dd className="text-slate-700">{finding.region}</dd>
              </div>
            )}
          </dl>
        </div>

        {/* Timeline */}
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Timeline</h3>
          <dl className="space-y-2 text-sm">
            <div>
              <dt className="text-slate-400 text-xs">First seen</dt>
              <dd className="text-slate-700">{finding.first_seen_at ? new Date(finding.first_seen_at).toLocaleDateString() : "—"}</dd>
            </div>
            <div>
              <dt className="text-slate-400 text-xs">Last seen</dt>
              <dd className="text-slate-700">{finding.last_seen_at ? new Date(finding.last_seen_at).toLocaleDateString() : "—"}</dd>
            </div>
            <div>
              <dt className="text-slate-400 text-xs">Source</dt>
              <dd className="text-slate-700 capitalize">{finding.primary_source.replace(/_/g, " ")}</dd>
            </div>
          </dl>
        </div>
      </div>

      {/* Remediation */}
      {finding.remediation && (
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Remediation</h3>
          <p className="text-sm text-slate-700 leading-relaxed">{finding.remediation}</p>
        </div>
      )}

      {/* Compliance frameworks */}
      {finding.compliance_frameworks?.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Compliance Frameworks</h3>
          <div className="flex flex-wrap gap-2">
            {finding.compliance_frameworks.map(fw => (
              <Badge key={fw} variant="default">{fw.replace(/_/g, " ")}</Badge>
            ))}
          </div>
        </div>
      )}

      {/* Sprint 18: AI Triage Panel — TriageAgent + AttackPathAnalyzerAgent */}
      <TriagePanel findingId={id} />

      {/* AI Insight */}
      <AiInsightCard findingId={id} />

      {/* Security Intelligence Panel */}
      <SecurityIntelligencePanel findingId={id} />

      {/* Status workflow */}
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Update Status</h3>
        <div className="flex flex-wrap gap-2">
          {STATUS_TRANSITIONS.filter(s => s !== finding.status).map(s => (
            <button
              key={s}
              onClick={() => handleStatusChange(s)}
              disabled={updating}
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm hover:bg-slate-50 disabled:opacity-50 transition-colors capitalize"
            >
              Mark as {s.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      {/* Assignment */}
      <AssignmentWidget findingId={id} />

      {/* Comments */}
      <CommentsSection findingId={id} />

      {/* Suppress modal */}
      {showSuppressModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-900 rounded-lg p-6 w-full max-w-md shadow-xl">
            <h3 className="text-lg font-semibold mb-2">Suppress Finding</h3>
            <p className="text-sm text-gray-500 mb-4">
              Provide a reason for suppressing this finding.
            </p>
            <textarea
              className="w-full border rounded p-2 text-sm min-h-[80px] resize-none"
              placeholder="e.g. Accepted risk, mitigated by compensating control..."
              value={suppressReason}
              onChange={(e) => setSuppressReason(e.target.value)}
            />
            <div className="flex gap-2 mt-4 justify-end">
              <button
                onClick={() => { setShowSuppressModal(false); setSuppressReason(""); }}
                className="px-4 py-2 text-sm border rounded hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSuppressSubmit}
                disabled={!suppressReason.trim() || suppressing}
                className="px-4 py-2 text-sm bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
              >
                {suppressing ? "Suppressing..." : "Suppress Finding"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
