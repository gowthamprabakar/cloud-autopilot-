"use client";

import { useState } from "react";
import {
  Building2, AlertTriangle, ShieldAlert, Clock, TrendingDown, TrendingUp,
  ArrowUpDown, BarChart3, ChevronRight
} from "lucide-react";
import { usePortfolioSummary, useSLABreaches, type WorkspaceSummary } from "@/lib/hooks/use-portfolio";
import { cn } from "@/lib/utils";

// ── Helpers ───────────────────────────────────────────────────────────────────

function RiskGauge({ score }: { score: number }) {
  const color = score > 70 ? "text-red-400" : score > 40 ? "text-orange-400" : "text-green-400";
  const bg = score > 70 ? "bg-red-500" : score > 40 ? "bg-orange-500" : "bg-green-500";
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div className={cn("h-full rounded-full", bg)} style={{ width: `${Math.min(score, 100)}%` }} />
      </div>
      <span className={cn("text-sm font-bold font-mono", color)}>{score}</span>
    </div>
  );
}

function SevBadge({ count, color }: { count: number; color: string }) {
  if (count === 0) return null;
  return <span className={cn("rounded px-1.5 py-0.5 text-[10px] font-medium", color)}>{count}</span>;
}

// ── Workspace Card ────────────────────────────────────────────────────────────

function WorkspaceRow({ ws }: { ws: WorkspaceSummary }) {
  return (
    <div className="flex items-center gap-4 px-4 py-3 bg-slate-800/50 border border-slate-700/50 rounded-lg hover:bg-slate-800 transition-colors">
      {/* Name + SLA */}
      <div className="flex items-center gap-2 w-48 shrink-0">
        <Building2 className="h-4 w-4 text-slate-500 shrink-0" />
        <span className="text-sm font-medium text-white truncate">{ws.workspace_name}</span>
        {ws.has_sla_breach && (
          <span className="shrink-0 h-2 w-2 rounded-full bg-red-500 animate-pulse" title="SLA breach" />
        )}
      </div>

      {/* Risk score */}
      <div className="w-28 shrink-0">
        <RiskGauge score={ws.risk_score} />
      </div>

      {/* Severity badges */}
      <div className="flex items-center gap-1.5 flex-1 min-w-0">
        <SevBadge count={ws.critical_count} color="bg-red-500/15 text-red-400 border border-red-500/30" />
        <SevBadge count={ws.high_count} color="bg-orange-500/15 text-orange-400 border border-orange-500/30" />
        <SevBadge count={ws.medium_count} color="bg-yellow-500/15 text-yellow-400 border border-yellow-500/30" />
        <SevBadge count={ws.low_count} color="bg-blue-500/15 text-blue-400 border border-blue-500/30" />
        <span className="text-xs text-slate-500 ml-1">{ws.open_findings} open</span>
      </div>

      {/* Trend */}
      <div className="w-16 shrink-0 flex items-center justify-end gap-1">
        {ws.trend_delta > 0 ? (
          <><TrendingUp className="h-3 w-3 text-red-400" /><span className="text-xs text-red-400">+{ws.trend_delta}</span></>
        ) : ws.trend_delta < 0 ? (
          <><TrendingDown className="h-3 w-3 text-green-400" /><span className="text-xs text-green-400">{ws.trend_delta}</span></>
        ) : (
          <span className="text-xs text-slate-500">—</span>
        )}
      </div>

      <ChevronRight className="h-4 w-4 text-slate-600 shrink-0" />
    </div>
  );
}

// ── SLA Breach Row ────────────────────────────────────────────────────────────

function BreachRow({ breach }: { breach: { finding_id: string; workspace_name: string; title: string; severity: string; sla_limit_hours: number; age_hours: number; remaining_hours: number; is_breached: boolean } }) {
  const sevColor: Record<string, string> = {
    critical: "bg-red-500/15 text-red-400",
    high: "bg-orange-500/15 text-orange-400",
    medium: "bg-yellow-500/15 text-yellow-400",
    low: "bg-blue-500/15 text-blue-400",
  };

  return (
    <div className="flex items-center gap-3 px-4 py-2.5 bg-slate-800/50 border border-slate-700/50 rounded-lg text-xs">
      <span className="w-32 shrink-0 text-slate-300 truncate">{breach.workspace_name}</span>
      <span className="flex-1 text-white truncate">{breach.title}</span>
      <span className={cn("shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium capitalize", sevColor[breach.severity] ?? sevColor.low)}>
        {breach.severity}
      </span>
      <span className="w-16 shrink-0 text-right text-slate-400">{breach.sla_limit_hours}h</span>
      <span className="w-16 shrink-0 text-right text-slate-400">{breach.age_hours.toFixed(0)}h</span>
      <span className={cn("w-20 shrink-0 text-right font-mono font-medium",
        breach.is_breached ? "text-red-400" : "text-yellow-400"
      )}>
        {breach.is_breached ? `${Math.abs(breach.remaining_hours).toFixed(0)}h over` : `${breach.remaining_hours.toFixed(0)}h left`}
      </span>
      <span className={cn("shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold uppercase",
        breach.is_breached ? "bg-red-600/20 text-red-400" : "bg-yellow-600/20 text-yellow-400"
      )}>
        {breach.is_breached ? "BREACHED" : "AT RISK"}
      </span>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function PortfolioPage() {
  const { portfolio, isLoading: pLoading } = usePortfolioSummary();
  const { breaches, isLoading: bLoading } = useSLABreaches();
  const [tab, setTab] = useState<"overview" | "sla">("overview");

  return (
    <main className="flex-1 overflow-y-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Portfolio</h1>
        <p className="text-sm text-slate-400 mt-0.5">
          MSP / vCISO multi-workspace overview
        </p>
      </div>

      {/* Summary cards */}
      {pLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {[...Array(5)].map((_, i) => <div key={i} className="h-24 rounded-xl bg-slate-800 animate-pulse" />)}
        </div>
      ) : portfolio ? (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="rounded-xl bg-slate-800 border border-slate-700/50 p-4">
            <div className="flex items-center gap-2 mb-1"><Building2 className="h-4 w-4 text-slate-400" /><span className="text-xs text-slate-400">Workspaces</span></div>
            <p className="text-2xl font-bold text-white">{portfolio.total_workspaces}</p>
          </div>
          <div className="rounded-xl bg-slate-800 border border-slate-700/50 p-4">
            <div className="flex items-center gap-2 mb-1"><AlertTriangle className="h-4 w-4 text-slate-400" /><span className="text-xs text-slate-400">Open Findings</span></div>
            <p className="text-2xl font-bold text-white">{portfolio.total_open_findings}</p>
          </div>
          <div className="rounded-xl bg-red-950/40 border border-red-500/20 p-4">
            <div className="flex items-center gap-2 mb-1"><ShieldAlert className="h-4 w-4 text-red-400" /><span className="text-xs text-red-400">Critical</span></div>
            <p className="text-2xl font-bold text-red-300">{portfolio.total_critical}</p>
          </div>
          <div className="rounded-xl bg-orange-950/30 border border-orange-500/20 p-4">
            <div className="flex items-center gap-2 mb-1"><Clock className="h-4 w-4 text-orange-400" /><span className="text-xs text-orange-400">SLA Breaches</span></div>
            <p className="text-2xl font-bold text-orange-300">{portfolio.sla_breach_count}</p>
          </div>
          <div className="rounded-xl bg-slate-800 border border-slate-700/50 p-4">
            <div className="flex items-center gap-2 mb-1"><BarChart3 className="h-4 w-4 text-slate-400" /><span className="text-xs text-slate-400">Avg Risk</span></div>
            <p className="text-2xl font-bold text-white">{portfolio.avg_risk_score}</p>
          </div>
        </div>
      ) : (
        <p className="text-sm text-red-400">Failed to load portfolio</p>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-slate-700/50 pb-0">
        <button
          onClick={() => setTab("overview")}
          className={cn("px-4 py-2 text-sm font-medium border-b-2 transition-colors",
            tab === "overview" ? "border-blue-500 text-blue-400" : "border-transparent text-slate-400 hover:text-white")}
        >
          <Building2 className="h-3.5 w-3.5 inline mr-1.5" />
          Portfolio Overview
          {portfolio && <span className="ml-1.5 text-[10px] bg-slate-700 rounded-full px-1.5 py-0.5">{portfolio.total_workspaces}</span>}
        </button>
        <button
          onClick={() => setTab("sla")}
          className={cn("px-4 py-2 text-sm font-medium border-b-2 transition-colors",
            tab === "sla" ? "border-blue-500 text-blue-400" : "border-transparent text-slate-400 hover:text-white")}
        >
          <Clock className="h-3.5 w-3.5 inline mr-1.5" />
          SLA Breaches
          {breaches.length > 0 && <span className="ml-1.5 text-[10px] bg-red-600/20 text-red-400 rounded-full px-1.5 py-0.5">{breaches.length}</span>}
        </button>
      </div>

      {/* Tab content */}
      {tab === "overview" && (
        <div className="space-y-2">
          {/* Column headers */}
          <div className="flex items-center gap-4 px-4 py-1.5 text-[10px] font-medium text-slate-500 uppercase tracking-wider">
            <span className="w-48 shrink-0">Workspace</span>
            <span className="w-28 shrink-0">Risk Score</span>
            <span className="flex-1">Severity Distribution</span>
            <span className="w-16 shrink-0 text-right">Trend</span>
            <span className="w-4 shrink-0" />
          </div>

          {pLoading ? (
            [...Array(4)].map((_, i) => <div key={i} className="h-14 rounded-lg bg-slate-800/50 animate-pulse" />)
          ) : portfolio && portfolio.workspaces.length > 0 ? (
            portfolio.workspaces.map(ws => <WorkspaceRow key={ws.workspace_id} ws={ws} />)
          ) : (
            <p className="py-12 text-center text-sm text-slate-500">No workspaces found.</p>
          )}
        </div>
      )}

      {tab === "sla" && (
        <div className="space-y-2">
          {/* Column headers */}
          <div className="flex items-center gap-3 px-4 py-1.5 text-[10px] font-medium text-slate-500 uppercase tracking-wider">
            <span className="w-32 shrink-0">Workspace</span>
            <span className="flex-1">Finding</span>
            <span className="w-16 shrink-0">Severity</span>
            <span className="w-16 shrink-0 text-right">SLA</span>
            <span className="w-16 shrink-0 text-right">Age</span>
            <span className="w-20 shrink-0 text-right">Remaining</span>
            <span className="w-16 shrink-0">Status</span>
          </div>

          {bLoading ? (
            [...Array(6)].map((_, i) => <div key={i} className="h-10 rounded-lg bg-slate-800/50 animate-pulse" />)
          ) : breaches.length > 0 ? (
            breaches.map(b => <BreachRow key={b.finding_id} breach={b} />)
          ) : (
            <p className="py-12 text-center text-sm text-slate-500">No SLA breaches across portfolio.</p>
          )}
        </div>
      )}
    </main>
  );
}
