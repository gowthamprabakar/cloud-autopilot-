"use client";

import { useState } from "react";
import {
  Radar, ShieldAlert, AlertTriangle, Activity,
  Filter, ChevronDown, ChevronRight, Zap, Shield
} from "lucide-react";
import {
  useDetectionSummary,
  useDetectionAlerts,
  type DetectionAlert,
} from "@/lib/hooks/use-detections";
import { cn } from "@/lib/utils";

// ── Helpers ───────────────────────────────────────────────────────────────────

const SEV_BADGE: Record<DetectionAlert["severity"], string> = {
  critical: "bg-red-500/10 text-red-400 border border-red-500/20",
  high:     "bg-orange-500/10 text-orange-400 border border-orange-500/20",
  medium:   "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20",
};

function riskColor(score: number): string {
  if (score >= 80) return "text-red-400";
  if (score >= 60) return "text-orange-400";
  if (score >= 40) return "text-yellow-400";
  return "text-slate-400";
}

function tacticBarColor(tactic: string): string {
  const t = tactic.toLowerCase();
  if (t.includes("privilege")) return "bg-red-500";
  if (t.includes("initial"))   return "bg-orange-500";
  if (t.includes("exfil"))     return "bg-yellow-500";
  return "bg-blue-500";
}

// ── Confidence bar ────────────────────────────────────────────────────────────

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 90 ? "bg-red-500" :
    pct >= 70 ? "bg-orange-500" :
    pct >= 50 ? "bg-yellow-500" :
    "bg-slate-500";
  return (
    <div className="flex items-center gap-2 min-w-0">
      <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all", color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-mono w-8 shrink-0 text-right text-slate-400">
        {value.toFixed(2)}
      </span>
    </div>
  );
}

// ── Alert Row ─────────────────────────────────────────────────────────────────

function AlertRow({ alert }: { alert: DetectionAlert }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-slate-700/50 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-3 bg-slate-800/50 hover:bg-slate-800 transition-colors text-left"
      >
        {/* Expand icon */}
        <span className="text-slate-500 shrink-0">
          {expanded
            ? <ChevronDown className="h-3.5 w-3.5" />
            : <ChevronRight className="h-3.5 w-3.5" />}
        </span>

        {/* Severity badge */}
        <span className={cn(
          "shrink-0 rounded px-2 py-0.5 text-[11px] font-medium capitalize",
          SEV_BADGE[alert.severity]
        )}>
          {alert.severity}
        </span>

        {/* Rule ID */}
        <span className="font-mono text-xs text-slate-300 w-40 shrink-0 truncate">
          {alert.rule_id}
        </span>

        {/* Tactic */}
        <span className="text-xs text-slate-400 w-36 shrink-0 truncate">
          {alert.tactic}
        </span>

        {/* Technique */}
        <span className="font-mono text-xs text-slate-400 w-28 shrink-0 truncate">
          {alert.technique}
        </span>

        {/* Confidence bar */}
        <div className="flex-1 min-w-0">
          <ConfidenceBar value={alert.confidence} />
        </div>

        {/* Risk score */}
        <span className={cn("shrink-0 text-xs font-semibold w-10 text-right font-mono", riskColor(alert.risk_score))}>
          {alert.risk_score}
        </span>

        {/* Affected resources count */}
        <span className="shrink-0 text-xs text-slate-400 w-16 text-right">
          {alert.affected_resources.length} res.
        </span>

        {/* Detected at */}
        <span className="shrink-0 text-xs text-slate-500 w-24 text-right">
          {new Date(alert.detected_at).toLocaleDateString()}
        </span>
      </button>

      {expanded && (
        <div className="border-t border-slate-700/50 bg-slate-900/60 px-4 py-3 space-y-3">
          {/* Description */}
          <p className="text-xs text-slate-300 leading-relaxed">{alert.description}</p>

          {/* Evidence */}
          {alert.evidence && (
            <div className="rounded bg-slate-800/70 border border-slate-700/40 px-3 py-2">
              <p className="text-[10px] font-medium text-slate-500 uppercase tracking-wider mb-1">Evidence</p>
              <p className="text-xs text-slate-300 font-mono leading-relaxed whitespace-pre-wrap break-all">
                {alert.evidence}
              </p>
            </div>
          )}

          {/* Affected resources */}
          {alert.affected_resources.length > 0 && (
            <div>
              <p className="text-xs font-medium text-slate-400 mb-2">
                Affected Resources ({alert.affected_resources.length})
              </p>
              <div className="space-y-1.5">
                {alert.affected_resources.map((r, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-3 text-xs bg-slate-800/50 rounded px-3 py-2"
                  >
                    <span className="shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
                      {r.type}
                    </span>
                    <span className="font-mono text-slate-300 truncate flex-1">{r.arn || "—"}</span>
                    <span className="shrink-0 text-slate-500 text-[10px]">{r.region}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function DetectionsPage() {
  const { summary, isLoading: sumLoading } = useDetectionSummary();
  const { alerts, isLoading: alertsLoading, error: alertsError } = useDetectionAlerts();

  const [sevFilter, setSevFilter]     = useState<string>("all");
  const [tacticFilter, setTacticFilter] = useState<string>("all");
  const [search, setSearch]           = useState("");

  const isLoading = sumLoading || alertsLoading;

  // Unique tactics from data for filter dropdown
  const uniqueTactics = Array.from(new Set(alerts.map(a => a.tactic))).sort();

  // Filter + sort by risk_score descending
  const filtered = alerts
    .filter(a => {
      if (sevFilter !== "all" && a.severity !== sevFilter) return false;
      if (tacticFilter !== "all" && a.tactic !== tacticFilter) return false;
      if (search) {
        const q = search.toLowerCase();
        if (
          !a.rule_id.toLowerCase().includes(q) &&
          !a.title.toLowerCase().includes(q) &&
          !a.tactic.toLowerCase().includes(q) &&
          !a.technique.toLowerCase().includes(q)
        ) return false;
      }
      return true;
    })
    .sort((a, b) => b.risk_score - a.risk_score);

  return (
    <main className="flex-1 overflow-y-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Detections</h1>
        <p className="text-sm text-slate-400 mt-0.5">
          Cloud Detection &amp; Response · Correlated security alerts
        </p>
      </div>

      {/* Summary stat cards */}
      {isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 rounded-xl bg-slate-800 animate-pulse" />
          ))}
        </div>
      ) : summary ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Total Alerts */}
          <div className="rounded-xl bg-slate-800 border border-slate-700/50 p-4">
            <div className="flex items-center gap-2 mb-1">
              <Radar className="h-4 w-4 text-slate-400" />
              <span className="text-xs text-slate-400">Total Alerts</span>
            </div>
            <p className="text-2xl font-bold text-white">{summary.total_alerts}</p>
            <p className="text-xs text-slate-500 mt-0.5">{summary.open_alerts} open</p>
          </div>

          {/* Critical */}
          <div className="rounded-xl bg-red-950/40 border border-red-500/20 p-4">
            <div className="flex items-center gap-2 mb-1">
              <ShieldAlert className="h-4 w-4 text-red-400" />
              <span className="text-xs text-red-400">Critical</span>
            </div>
            <p className="text-2xl font-bold text-red-300">{summary.critical_count}</p>
            <p className="text-xs text-red-400/70 mt-0.5">Immediate action required</p>
          </div>

          {/* High */}
          <div className="rounded-xl bg-orange-950/30 border border-orange-500/20 p-4">
            <div className="flex items-center gap-2 mb-1">
              <AlertTriangle className="h-4 w-4 text-orange-400" />
              <span className="text-xs text-orange-400">High</span>
            </div>
            <p className="text-2xl font-bold text-orange-300">{summary.high_count}</p>
            <p className="text-xs text-orange-400/70 mt-0.5">Elevated risk</p>
          </div>

          {/* Avg Confidence */}
          <div className="rounded-xl bg-slate-800 border border-slate-700/50 p-4">
            <div className="flex items-center gap-2 mb-1">
              <Activity className="h-4 w-4 text-slate-400" />
              <span className="text-xs text-slate-400">Avg Confidence</span>
            </div>
            <p className="text-2xl font-bold text-white">
              {Math.round(summary.avg_confidence * 100)}%
            </p>
            <p className="text-xs text-slate-500 mt-0.5">{summary.rules_fired} rules fired</p>
          </div>
        </div>
      ) : null}

      {/* By Tactic breakdown */}
      {!isLoading && summary && Object.keys(summary.by_tactic).length > 0 && (
        <div className="rounded-xl bg-slate-800 border border-slate-700/50 p-4">
          <div className="flex items-center gap-2 mb-3">
            <Zap className="h-4 w-4 text-slate-400" />
            <span className="text-sm font-medium text-white">Alerts by Tactic</span>
          </div>
          <div className="space-y-2">
            {Object.entries(summary.by_tactic)
              .sort((a, b) => b[1] - a[1])
              .map(([tactic, count]) => {
                const maxVal = Math.max(...Object.values(summary.by_tactic));
                const pct = maxVal > 0 ? (count / maxVal) * 100 : 0;
                return (
                  <div key={tactic} className="flex items-center gap-3">
                    <span className="text-xs text-slate-400 w-44 shrink-0 truncate">{tactic}</span>
                    <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className={cn("h-full rounded-full", tacticBarColor(tactic))}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="text-xs text-slate-300 w-6 text-right">{count}</span>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* Alert Feed */}
      <div className="rounded-xl bg-slate-800 border border-slate-700/50">
        {/* Filter bar */}
        <div className="flex flex-wrap items-center gap-3 px-4 py-3 border-b border-slate-700/50">
          <div className="flex items-center gap-2">
            <Filter className="h-3.5 w-3.5 text-slate-400" />
            <span className="text-xs text-slate-400 font-medium">Filter:</span>
          </div>

          {/* Severity filter */}
          <select
            value={sevFilter}
            onChange={e => setSevFilter(e.target.value)}
            className="rounded-md border border-slate-600 bg-slate-700 px-2 py-1 text-xs text-white focus:outline-none"
          >
            <option value="all">All severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
          </select>

          {/* Tactic filter */}
          <select
            value={tacticFilter}
            onChange={e => setTacticFilter(e.target.value)}
            className="rounded-md border border-slate-600 bg-slate-700 px-2 py-1 text-xs text-white focus:outline-none"
          >
            <option value="all">All tactics</option>
            {uniqueTactics.map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>

          {/* Search */}
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search rule, tactic…"
            className="rounded-md border border-slate-600 bg-slate-700 px-2.5 py-1 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-blue-500 w-44"
          />

          <span className="ml-auto text-xs text-slate-500">{filtered.length} alerts</span>
        </div>

        {/* Column headers */}
        <div className="flex items-center gap-3 px-4 py-2 border-b border-slate-700/30 bg-slate-900/30">
          <span className="w-3.5 shrink-0" />
          <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider w-16 shrink-0">Severity</span>
          <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider w-40 shrink-0">Rule</span>
          <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider w-36 shrink-0">Tactic</span>
          <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider w-28 shrink-0">Technique</span>
          <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider flex-1">Confidence</span>
          <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider w-10 text-right shrink-0">Risk</span>
          <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider w-16 text-right shrink-0">Resources</span>
          <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider w-24 text-right shrink-0">Detected</span>
        </div>

        {/* Rows */}
        <div className="p-3 space-y-1.5">
          {alertsLoading ? (
            [...Array(6)].map((_, i) => (
              <div key={i} className="h-12 rounded-lg bg-slate-700/50 animate-pulse" />
            ))
          ) : alertsError ? (
            <p className="py-8 text-center text-sm text-red-400">
              Failed to load detection alerts
            </p>
          ) : filtered.length === 0 ? (
            <p className="py-8 text-center text-sm text-slate-500">
              No alerts match filters.
            </p>
          ) : (
            filtered.map(alert => <AlertRow key={alert.id} alert={alert} />)
          )}
        </div>
      </div>
    </main>
  );
}
