"use client";
import { useState } from "react";
import Link from "next/link";
import { CheckCircle2 } from "lucide-react";
import { useMyAssignments } from "@/lib/hooks/use-assignments";
import { useSlaFindings, useSlaSummary } from "@/lib/hooks/use-sla";
import { Spinner } from "@/components/ui/spinner";
import type { SlaFinding } from "@/lib/types";

// ── Severity badge ─────────────────────────────────────────────────────────

function SeverityBadge({ severity }: { severity: string }) {
  const styles: Record<string, string> = {
    critical: "bg-red-100 text-red-700",
    high: "bg-orange-100 text-orange-700",
    medium: "bg-yellow-100 text-yellow-700",
    low: "bg-blue-100 text-blue-700",
    info: "bg-slate-100 text-slate-600",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold capitalize ${styles[severity.toLowerCase()] ?? "bg-slate-100 text-slate-600"}`}
    >
      {severity}
    </span>
  );
}

// ── SLA status badge ───────────────────────────────────────────────────────

type SlaStatus = SlaFinding["sla_status"];

function SlaStatusBadge({ status }: { status: SlaStatus }) {
  const styles: Record<SlaStatus, string> = {
    breached: "bg-red-100 text-red-700",
    at_risk: "bg-amber-100 text-amber-700",
    on_track: "bg-green-100 text-green-700",
    resolved: "bg-slate-100 text-slate-500",
  };
  const labels: Record<SlaStatus, string> = {
    breached: "Breached",
    at_risk: "At Risk",
    on_track: "On Track",
    resolved: "Resolved",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${styles[status]}`}
    >
      {labels[status]}
    </span>
  );
}

// ── Derive SLA status from due_date for assignments ────────────────────────

function deriveSlaStatus(dueDateStr: string | null): SlaStatus {
  if (!dueDateStr) return "on_track";
  const due = new Date(dueDateStr).getTime();
  const now = Date.now();
  const diff = due - now;
  const oneDayMs = 86_400_000;
  if (diff < 0) return "breached";
  if (diff < oneDayMs * 3) return "at_risk";
  return "on_track";
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "No deadline";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

// ── Days remaining cell ────────────────────────────────────────────────────

function DaysRemaining({
  days,
  total,
}: {
  days: number | null;
  total: number | null;
}) {
  if (days === null) return <span className="text-slate-400 font-mono">—</span>;

  const threshold = total !== null ? total * 0.2 : 5;
  const color =
    days < 0
      ? "text-red-600 font-semibold"
      : days <= threshold
        ? "text-amber-600 font-semibold"
        : "text-green-700";

  return (
    <span className={`font-mono text-sm ${color}`}>
      {days < 0 ? `${Math.abs(days)}d overdue` : `${days}d left`}
    </span>
  );
}

// ── Filter tabs ────────────────────────────────────────────────────────────

type FilterTab = "all" | "breached" | "at_risk" | "on_track";

const TABS: { value: FilterTab; label: string }[] = [
  { value: "all", label: "All" },
  { value: "breached", label: "Breached" },
  { value: "at_risk", label: "At Risk" },
  { value: "on_track", label: "On Track" },
];

// ── Page ──────────────────────────────────────────────────────────────────

export default function RemediationPage() {
  const [activeTab, setActiveTab] = useState<FilterTab>("all");
  const { assignments, isLoading: assignmentsLoading } = useMyAssignments();
  const { summary, isLoading: summaryLoading } = useSlaSummary();
  const {
    findings: slaFindings,
    isLoading: slaLoading,
  } = useSlaFindings(activeTab === "all" ? undefined : activeTab);

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900">Remediation</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Track your assigned findings and SLA compliance.
        </p>
      </div>

      {/* ── Section 1: My Assignments ─────────────────────────────────────── */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <h2 className="text-sm font-semibold text-slate-700">My Assignments</h2>
          {!assignmentsLoading && (
            <span className="inline-flex items-center justify-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-600">
              {assignments.length}
            </span>
          )}
        </div>

        {assignmentsLoading ? (
          <div className="flex justify-center py-8">
            <Spinner className="h-5 w-5" />
          </div>
        ) : assignments.length === 0 ? (
          <div className="rounded-xl border border-slate-200 bg-white p-10 flex flex-col items-center gap-3 text-center">
            <CheckCircle2 className="h-8 w-8 text-green-400" />
            <p className="text-sm font-medium text-slate-600">
              No findings assigned to you
            </p>
            <p className="text-xs text-slate-400">
              When a finding is assigned to you, it will appear here.
            </p>
          </div>
        ) : (
          <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
                    Finding Title
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
                    Severity
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
                    Due Date
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
                    SLA Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {assignments.map((a) => {
                  const slaStatus = deriveSlaStatus(a.due_date);
                  return (
                    <tr key={a.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-4 py-3">
                        <p className="font-medium text-slate-800 max-w-xs truncate">
                          {a.finding_id}
                        </p>
                        {a.note && (
                          <p className="text-xs text-slate-400 truncate max-w-xs">
                            {a.note}
                          </p>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-xs text-slate-400">—</span>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-600">
                        {formatDate(a.due_date)}
                      </td>
                      <td className="px-4 py-3">
                        <SlaStatusBadge status={slaStatus} />
                      </td>
                      <td className="px-4 py-3">
                        <Link
                          href={`/dashboard/findings/${a.finding_id}`}
                          className="text-sm text-blue-600 hover:underline"
                        >
                          View Finding
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* ── Section 2: SLA Overview ───────────────────────────────────────── */}
      <section>
        <h2 className="text-sm font-semibold text-slate-700 mb-3">SLA Overview</h2>

        {/* Metric cards */}
        {summaryLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
            {[...Array(3)].map((_, i) => (
              <div
                key={i}
                className="rounded-xl border border-slate-200 bg-white p-5 animate-pulse space-y-2"
              >
                <div className="h-3 w-20 rounded bg-slate-100" />
                <div className="h-8 w-12 rounded bg-slate-200" />
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
            <div className="rounded-xl border border-red-100 bg-red-50 p-5">
              <p className="text-xs font-semibold text-red-600 uppercase tracking-wide">
                Breached
              </p>
              <p className="text-3xl font-bold text-red-700 mt-1">
                {summary.breached.toLocaleString()}
              </p>
            </div>
            <div className="rounded-xl border border-amber-100 bg-amber-50 p-5">
              <p className="text-xs font-semibold text-amber-600 uppercase tracking-wide">
                At Risk
              </p>
              <p className="text-3xl font-bold text-amber-700 mt-1">
                {summary.at_risk.toLocaleString()}
              </p>
            </div>
            <div className="rounded-xl border border-green-100 bg-green-50 p-5">
              <p className="text-xs font-semibold text-green-700 uppercase tracking-wide">
                On Track
              </p>
              <p className="text-3xl font-bold text-green-700 mt-1">
                {summary.on_track.toLocaleString()}
              </p>
            </div>
          </div>
        )}

        {/* Filter tabs */}
        <div className="flex gap-1 mb-4">
          {TABS.map((tab) => (
            <button
              key={tab.value}
              onClick={() => setActiveTab(tab.value)}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                activeTab === tab.value
                  ? "bg-blue-600 text-white"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* SLA findings table */}
        {slaLoading ? (
          <div className="flex justify-center py-8">
            <Spinner className="h-5 w-5" />
          </div>
        ) : slaFindings.length === 0 ? (
          <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-400">
            No findings for this filter.
          </div>
        ) : (
          <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
                    Title
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
                    Severity
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
                    Days Remaining
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
                    Due Date
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
                    Status
                  </th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {slaFindings.map((f) => (
                  <tr key={f.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3">
                      <p className="font-medium text-slate-800 max-w-xs truncate">
                        {f.title}
                      </p>
                    </td>
                    <td className="px-4 py-3">
                      <SeverityBadge severity={f.severity} />
                    </td>
                    <td className="px-4 py-3">
                      <DaysRemaining
                        days={f.sla_days_remaining}
                        total={f.sla_days_total}
                      />
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600">
                      {formatDate(f.sla_due_date)}
                    </td>
                    <td className="px-4 py-3">
                      <SlaStatusBadge status={f.sla_status} />
                    </td>
                    <td className="px-4 py-3">
                      <Link
                        href={`/dashboard/findings/${f.id}`}
                        className="text-sm text-blue-600 hover:underline"
                      >
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
