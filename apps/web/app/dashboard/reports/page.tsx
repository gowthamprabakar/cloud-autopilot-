"use client";
import useSWR from "swr";
import { apiFetcher } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import type { ExecutiveSummaryResponse, Severity } from "@/lib/types";
import { Printer } from "lucide-react";

// ── Skeleton helpers ──────────────────────────────────────────────────────

function StatCardSkeleton() {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-2 animate-pulse">
      <div className="h-3 w-24 rounded bg-slate-100" />
      <div className="h-8 w-16 rounded bg-slate-200" />
    </div>
  );
}

function SectionSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-3 animate-pulse">
      <div className="h-4 w-40 rounded bg-slate-100" />
      {[...Array(rows)].map((_, i) => (
        <div key={i} className="h-4 rounded bg-slate-100" style={{ width: `${60 + i * 10}%` }} />
      ))}
    </div>
  );
}

// ── Risk score bar ────────────────────────────────────────────────────────

function RiskBar({ score }: { score: number | null }) {
  if (score === null) return <span className="text-xs text-slate-400 font-mono">—</span>;
  const pct = Math.min(100, (score / 10) * 100);
  const color =
    score >= 8 ? "bg-red-500" :
    score >= 6 ? "bg-orange-500" :
    score >= 4 ? "bg-amber-500" :
    score >= 2 ? "bg-yellow-500" :
    "bg-slate-300";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 rounded-full bg-slate-100 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-slate-600">{score.toFixed(1)}</span>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────

export default function ReportsPage() {
  const { data: summary, isLoading, error } = useSWR<ExecutiveSummaryResponse>(
    "/api/v1/reports/executive-summary",
    apiFetcher
  );

  return (
    <>
      <style>{`@media print { .no-print { display: none; } }`}</style>

      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between no-print">
          <div>
            <h1 className="text-xl font-bold text-slate-900">Executive Summary</h1>
            {summary && (
              <p className="text-sm text-slate-500 mt-0.5">
                Generated {new Date(summary.generated_at).toLocaleString()} &middot; Last {summary.period_days} days
              </p>
            )}
          </div>
          <button
            onClick={() => window.print()}
            className="no-print inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
          >
            <Printer className="h-4 w-4" />
            Print
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-5 text-center text-sm text-red-600">
            Failed to load executive summary. Please try again.
          </div>
        )}

        {/* Key Metrics */}
        <section>
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Key Metrics</h2>
          {isLoading ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[...Array(4)].map((_, i) => <StatCardSkeleton key={i} />)}
            </div>
          ) : summary && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="rounded-xl border border-slate-200 bg-white p-5">
                <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">Total Findings</p>
                <p className="text-3xl font-bold text-slate-900 mt-1">{summary.total_findings.toLocaleString()}</p>
                <p className="text-xs text-slate-400 mt-1">{summary.open_findings} open</p>
              </div>
              <div className="rounded-xl border border-red-100 bg-red-50 p-5">
                <p className="text-xs text-red-600 uppercase tracking-wide font-semibold">Critical Open</p>
                <p className="text-3xl font-bold text-red-700 mt-1">{summary.critical_open.toLocaleString()}</p>
                <p className="text-xs text-red-400 mt-1">{summary.high_open} high open</p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-5">
                <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">New (7d)</p>
                <p className="text-3xl font-bold text-slate-900 mt-1">{summary.new_last_7_days.toLocaleString()}</p>
                <p className="text-xs text-slate-400 mt-1">{summary.resolved_last_7_days} resolved</p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-5">
                <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">Avg Risk Score</p>
                <p className="text-3xl font-bold text-slate-900 mt-1">
                  {summary.avg_risk_score !== null ? summary.avg_risk_score.toFixed(1) : "—"}
                </p>
                <p className="text-xs text-slate-400 mt-1">out of 10.0</p>
              </div>
            </div>
          )}
        </section>

        {/* MTTR */}
        {isLoading ? (
          <SectionSkeleton rows={1} />
        ) : summary && (
          <section className="rounded-xl border border-slate-200 bg-white p-5">
            <h2 className="text-sm font-semibold text-slate-700 mb-2">Mean Time to Resolve</h2>
            {summary.mttr_days !== null ? (
              <p className="text-slate-600 text-sm">
                Mean time to resolve: <span className="font-bold text-slate-900">{summary.mttr_days.toFixed(1)} days</span>
              </p>
            ) : (
              <p className="text-sm text-slate-400">No resolved findings yet</p>
            )}
          </section>
        )}

        {/* Top Riskiest Findings */}
        <section>
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Top 10 Riskiest Open Findings</h2>
          {isLoading ? (
            <SectionSkeleton rows={5} />
          ) : summary && (
            <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
              {summary.top_findings.length === 0 ? (
                <p className="p-6 text-center text-sm text-slate-400">No findings to display</p>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50">
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Title</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Severity</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Risk Score</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide hidden md:table-cell">Resource</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {summary.top_findings.map((f) => (
                      <tr key={f.id} className="hover:bg-slate-50 transition-colors">
                        <td className="px-4 py-3">
                          <p className="font-medium text-slate-800 line-clamp-2 max-w-[300px]">{f.title}</p>
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant={f.severity as Severity}>{f.severity}</Badge>
                        </td>
                        <td className="px-4 py-3">
                          <RiskBar score={f.risk_score} />
                        </td>
                        <td className="px-4 py-3 hidden md:table-cell">
                          <p className="text-xs text-slate-500 font-mono truncate max-w-[200px]">
                            {f.resource_arn ?? f.resource_type ?? "—"}
                          </p>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </section>

        {/* Per-Account Breakdown */}
        <section>
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Per-Account Breakdown</h2>
          {isLoading ? (
            <SectionSkeleton rows={3} />
          ) : summary && (
            <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
              {summary.accounts.length === 0 ? (
                <p className="p-6 text-center text-sm text-slate-400">No account data available</p>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50">
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Account</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Open</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Critical</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {summary.accounts.map((acct) => (
                      <tr key={acct.account_id} className="hover:bg-slate-50 transition-colors">
                        <td className="px-4 py-3">
                          <p className="font-medium text-slate-800">{acct.account_alias ?? acct.account_id}</p>
                          {acct.account_alias && (
                            <p className="text-xs text-slate-400 font-mono">{acct.account_id}</p>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <span className="font-mono text-sm text-slate-700">{acct.open_findings}</span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`font-mono text-sm ${acct.critical_findings > 0 ? "text-red-600 font-bold" : "text-slate-700"}`}>
                            {acct.critical_findings}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="font-mono text-sm text-slate-500">{acct.total_findings}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </section>

        {/* Compliance Coverage */}
        <section>
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Compliance Coverage</h2>
          {isLoading ? (
            <SectionSkeleton rows={4} />
          ) : summary && (
            <div className="rounded-xl border border-slate-200 bg-white p-5">
              {summary.compliance.length === 0 ? (
                <p className="text-sm text-slate-400">No compliance data available</p>
              ) : (
                <div className="space-y-4">
                  {summary.compliance.map((fw) => {
                    const pct = Math.round(fw.coverage_pct);
                    const color =
                      pct >= 80 ? "bg-green-500" :
                      pct >= 60 ? "bg-amber-500" :
                      "bg-red-500";
                    return (
                      <div key={fw.framework_id}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-slate-700">{fw.framework_id.replace(/_/g, " ").toUpperCase()}</span>
                          <span className="text-sm font-bold text-slate-900">{pct}%</span>
                        </div>
                        <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${color} transition-all`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <p className="text-xs text-slate-400 mt-1">{fw.passing} / {fw.total} controls passing</p>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </>
  );
}
