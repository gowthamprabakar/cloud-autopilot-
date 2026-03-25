"use client";

import { useState } from "react";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  ShieldAlert,
  AlertTriangle,
  Info,
  BarChart2,
  Building2,
  Flame,
} from "lucide-react";
import { useExecutiveSummary, useExecutiveTrend } from "@/lib/hooks/use-executive";
import { Spinner } from "@/components/ui/spinner";
import Link from "next/link";

// ── Helpers ───────────────────────────────────────────────────────────────────

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(" ");
}

const SEV_COLORS: Record<string, string> = {
  critical: "text-red-600 bg-red-50 border-red-200",
  high: "text-orange-600 bg-orange-50 border-orange-200",
  medium: "text-yellow-600 bg-yellow-50 border-yellow-200",
  low: "text-blue-600 bg-blue-50 border-blue-200",
  info: "text-slate-500 bg-slate-50 border-slate-200",
};

const SEV_BAR: Record<string, string> = {
  critical: "bg-red-500",
  high: "bg-orange-400",
  medium: "bg-yellow-400",
  low: "bg-blue-400",
  info: "bg-slate-300",
};

function scoreColor(score: number) {
  if (score >= 75) return "text-emerald-600";
  if (score >= 50) return "text-yellow-600";
  if (score >= 25) return "text-orange-600";
  return "text-red-600";
}

function scoreRing(score: number) {
  if (score >= 75) return "stroke-emerald-500";
  if (score >= 50) return "stroke-yellow-500";
  if (score >= 25) return "stroke-orange-500";
  return "stroke-red-500";
}

function scoreLabel(score: number) {
  if (score >= 75) return "Good";
  if (score >= 50) return "Fair";
  if (score >= 25) return "At Risk";
  return "Critical";
}

function pct(n: number) {
  return `${Math.round(n * 100)}%`;
}

// ── Risk Gauge ────────────────────────────────────────────────────────────────

function RiskGauge({ score }: { score: number }) {
  const r = 54;
  const circ = 2 * Math.PI * r;
  // Half-circle gauge: use 180° arc
  const halfCirc = Math.PI * r;
  const filled = (score / 100) * halfCirc;

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width="140" height="80" viewBox="0 0 140 80">
        {/* Background arc */}
        <path
          d="M 10 74 A 60 60 0 0 1 130 74"
          fill="none"
          stroke="#e2e8f0"
          strokeWidth="12"
          strokeLinecap="round"
        />
        {/* Score arc */}
        <path
          d="M 10 74 A 60 60 0 0 1 130 74"
          fill="none"
          className={scoreRing(score)}
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={`${(score / 100) * 188.5} 188.5`}
        />
        {/* Score text */}
        <text
          x="70"
          y="65"
          textAnchor="middle"
          className="text-2xl font-bold"
          fill="currentColor"
          fontSize="28"
          fontWeight="bold"
        >
          {score}
        </text>
      </svg>
      <span className={cn("text-sm font-semibold", scoreColor(score))}>
        {scoreLabel(score)}
      </span>
    </div>
  );
}

// ── Mini Bar Chart ────────────────────────────────────────────────────────────

function TrendChart({ data }: { data: { date: string; open: number; new: number }[] }) {
  if (!data.length) return null;
  const maxOpen = Math.max(...data.map(d => d.open), 1);
  // Show every 5th label
  const step = Math.ceil(data.length / 6);

  return (
    <div className="flex items-end gap-0.5 h-28 w-full">
      {data.map((d, i) => {
        const h = Math.max(2, Math.round((d.open / maxOpen) * 100));
        const showLabel = i % step === 0 || i === data.length - 1;
        return (
          <div key={d.date} className="flex flex-col items-center flex-1 gap-0.5" title={`${d.date}: ${d.open} open, ${d.new} new`}>
            <div
              className="w-full rounded-sm bg-blue-400 hover:bg-blue-500 transition-colors"
              style={{ height: `${h}%` }}
            />
            {showLabel && (
              <span className="text-[9px] text-slate-400 rotate-45 origin-left whitespace-nowrap">
                {d.date.slice(5)}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function ExecutivePage() {
  const { summary, isLoading } = useExecutiveSummary();
  const [trendDays, setTrendDays] = useState<30 | 60 | 90>(30);
  const { trend, isLoading: trendLoading } = useExecutiveTrend(trendDays);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner />
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="text-center py-20 text-slate-500">
        Failed to load executive summary.
      </div>
    );
  }

  const { risk_score, trend: trendDir, trend_delta, open_findings, total_findings, by_severity, sla_compliance, accounts, top_findings } = summary;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Executive Dashboard</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Risk posture summary · {new Date().toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}
          </p>
        </div>
        <span className="text-xs text-slate-400 italic">{summary.score_formula}</span>
      </div>

      {/* Top row: Score + severity breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Risk score card */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 flex flex-col items-center gap-3 shadow-sm">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-700 self-start">
            <ShieldAlert className="h-4 w-4 text-slate-500" />
            Risk Posture Score
          </div>
          <RiskGauge score={risk_score} />
          <div className="flex items-center gap-1.5 text-sm">
            {trendDir === "improving" ? (
              <TrendingUp className="h-4 w-4 text-emerald-500" />
            ) : trendDir === "worsening" ? (
              <TrendingDown className="h-4 w-4 text-red-500" />
            ) : (
              <Minus className="h-4 w-4 text-slate-400" />
            )}
            <span className={cn(
              "font-medium",
              trendDir === "improving" ? "text-emerald-600" : trendDir === "worsening" ? "text-red-600" : "text-slate-500"
            )}>
              {trendDir === "stable" ? "Stable" : `${Math.abs(trend_delta)} pts ${trendDir}`} vs 30 days ago
            </span>
          </div>
          <div className="text-xs text-slate-400">
            {open_findings} open · {total_findings} total findings
          </div>
        </div>

        {/* Severity breakdown */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-4">
            <AlertTriangle className="h-4 w-4 text-slate-500" />
            Findings by Severity
          </div>
          <div className="space-y-3">
            {(["critical", "high", "medium", "low", "info"] as const).map(sev => {
              const bucket = by_severity[sev] ?? { open: 0, total: 0 };
              const openPct = bucket.total > 0 ? bucket.open / bucket.total : 0;
              return (
                <div key={sev} className="flex items-center gap-3">
                  <span className={cn(
                    "w-16 text-xs font-semibold capitalize px-2 py-0.5 rounded border text-center",
                    SEV_COLORS[sev]
                  )}>
                    {sev}
                  </span>
                  <div className="flex-1 bg-slate-100 rounded-full h-2">
                    <div
                      className={cn("h-2 rounded-full transition-all", SEV_BAR[sev])}
                      style={{ width: `${Math.round(openPct * 100)}%` }}
                    />
                  </div>
                  <span className="text-xs text-slate-600 w-20 text-right">
                    {bucket.open} / {bucket.total} open
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* SLA Compliance */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-4">
          <Info className="h-4 w-4 text-slate-500" />
          SLA Compliance
          <span className="text-xs font-normal text-slate-400">— % of open findings still within SLA window</span>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {([
            { key: "critical", label: "Critical", window: "24h" },
            { key: "high",     label: "High",     window: "7 days" },
            { key: "medium",   label: "Medium",   window: "30 days" },
            { key: "low",      label: "Low",      window: "90 days" },
          ] as const).map(({ key, label, window }) => {
            const val = sla_compliance[key] ?? 1;
            const color = val >= 0.8 ? "text-emerald-600" : val >= 0.5 ? "text-yellow-600" : "text-red-600";
            const bar = val >= 0.8 ? "bg-emerald-400" : val >= 0.5 ? "bg-yellow-400" : "bg-red-400";
            return (
              <div key={key} className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500">{label} <span className="text-slate-400">({window})</span></span>
                  <span className={cn("text-sm font-bold", color)}>{pct(val)}</span>
                </div>
                <div className="bg-slate-100 rounded-full h-1.5">
                  <div className={cn("h-1.5 rounded-full", bar)} style={{ width: pct(val) }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Trend chart */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
            <BarChart2 className="h-4 w-4 text-slate-500" />
            Open Findings Trend
          </div>
          <div className="flex gap-1">
            {([30, 60, 90] as const).map(d => (
              <button
                key={d}
                onClick={() => setTrendDays(d)}
                className={cn(
                  "px-2.5 py-1 text-xs rounded font-medium transition-colors",
                  trendDays === d
                    ? "bg-blue-600 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                )}
              >
                {d}d
              </button>
            ))}
          </div>
        </div>
        {trendLoading ? (
          <div className="flex justify-center h-28 items-center"><Spinner /></div>
        ) : trend ? (
          <TrendChart data={trend.data_points} />
        ) : null}
      </div>

      {/* Bottom row: accounts + top findings */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Account risk breakdown */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-4">
            <Building2 className="h-4 w-4 text-slate-500" />
            Account Risk Breakdown
          </div>
          {accounts.length === 0 ? (
            <p className="text-sm text-slate-400">No accounts connected.</p>
          ) : (
            <div className="space-y-3">
              {accounts.map(acct => (
                <div key={acct.id} className="flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-slate-700 truncate">{acct.alias}</span>
                      <span className={cn("text-sm font-bold ml-2", scoreColor(acct.risk_score))}>
                        {acct.risk_score}
                      </span>
                    </div>
                    <div className="bg-slate-100 rounded-full h-1.5">
                      <div
                        className={cn(
                          "h-1.5 rounded-full",
                          acct.risk_score >= 75 ? "bg-emerald-400" :
                          acct.risk_score >= 50 ? "bg-yellow-400" :
                          acct.risk_score >= 25 ? "bg-orange-400" : "bg-red-500"
                        )}
                        style={{ width: `${acct.risk_score}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-slate-400">{acct.open_findings} open findings</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Top findings */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-4">
            <Flame className="h-4 w-4 text-red-500" />
            Top Risk Findings
          </div>
          {top_findings.length === 0 ? (
            <p className="text-sm text-slate-400">No open findings.</p>
          ) : (
            <div className="space-y-2">
              {top_findings.map((f, i) => (
                <Link
                  key={f.id}
                  href={`/dashboard/findings/${f.id}`}
                  className="flex items-start gap-3 p-2.5 rounded-lg hover:bg-slate-50 transition-colors group"
                >
                  <span className="text-xs font-bold text-slate-400 mt-0.5 w-4 shrink-0">#{i + 1}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-slate-800 truncate group-hover:text-blue-600">{f.title}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className={cn(
                        "text-[10px] font-semibold capitalize px-1.5 py-0.5 rounded border",
                        SEV_COLORS[f.severity]
                      )}>
                        {f.severity}
                      </span>
                      {f.resource_type && (
                        <span className="text-[10px] text-slate-400 truncate">{f.resource_type}</span>
                      )}
                    </div>
                  </div>
                  <span className="text-xs font-bold text-slate-600 shrink-0">
                    {f.risk_score?.toFixed(1)}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
