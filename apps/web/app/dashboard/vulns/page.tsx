"use client";

import { useState } from "react";
import {
  Bug, ShieldAlert, Zap, AlertTriangle, ChevronDown, ChevronRight,
  ExternalLink, Filter, TrendingUp, Activity
} from "lucide-react";
import { useVulnSummary, useVulnInventory, type VulnItem } from "@/lib/hooks/use-vulns";
import { cn } from "@/lib/utils";

// ── Helpers ───────────────────────────────────────────────────────────────────

const SEV_COLOR: Record<string, string> = {
  critical: "bg-red-500/10 text-red-400 border border-red-500/20",
  high:     "bg-orange-500/10 text-orange-400 border border-orange-500/20",
  medium:   "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20",
  low:      "bg-blue-500/10 text-blue-400 border border-blue-500/20",
};

const TIER_COLOR: Record<string, string> = {
  imminent: "bg-red-500/15 text-red-300 border border-red-500/30",
  high:     "bg-orange-500/15 text-orange-300 border border-orange-500/30",
  elevated: "bg-yellow-500/15 text-yellow-300 border border-yellow-500/30",
  moderate: "bg-slate-600/40 text-slate-300 border border-slate-500/30",
};

function EpssBar({ score }: { score: number | null }) {
  const pct = Math.round((score ?? 0) * 100);
  const color =
    pct >= 90 ? "bg-red-500" :
    pct >= 50 ? "bg-orange-500" :
    pct >= 10 ? "bg-yellow-500" :
    "bg-slate-600";
  return (
    <div className="flex items-center gap-2 min-w-0">
      <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div className={cn("h-full rounded-full transition-all", color)} style={{ width: `${pct}%` }} />
      </div>
      <span className={cn("text-xs font-mono w-10 shrink-0 text-right",
        pct >= 90 ? "text-red-400" : pct >= 50 ? "text-orange-400" : "text-slate-400"
      )}>
        {score !== null ? score.toFixed(3) : "—"}
      </span>
    </div>
  );
}

// ── CVE Row ───────────────────────────────────────────────────────────────────

function CVERow({ item }: { item: VulnItem }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-slate-700/50 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-3 bg-slate-800/50 hover:bg-slate-800 transition-colors text-left"
      >
        {/* Expand icon */}
        <span className="text-slate-500 shrink-0">
          {expanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        </span>

        {/* CVE ID */}
        <span className="font-mono text-sm font-semibold text-white w-40 shrink-0">
          {item.cve_id}
        </span>

        {/* KEV badge */}
        {item.in_kev ? (
          <span className="shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold uppercase bg-red-600/20 text-red-400 border border-red-500/30">
            KEV
          </span>
        ) : (
          <span className="shrink-0 w-9" />
        )}

        {/* Severity */}
        <span className={cn("shrink-0 rounded px-2 py-0.5 text-[11px] font-medium capitalize", SEV_COLOR[item.severity] ?? SEV_COLOR.low)}>
          {item.severity}
        </span>

        {/* EPSS bar */}
        <div className="flex-1 min-w-0">
          <EpssBar score={item.epss_score} />
        </div>

        {/* Risk tier */}
        <span className={cn("shrink-0 rounded px-2 py-0.5 text-[11px] font-medium capitalize", TIER_COLOR[item.risk_tier])}>
          {item.risk_tier}
        </span>

        {/* CVSS */}
        <span className="shrink-0 text-xs text-slate-400 w-14 text-right font-mono">
          CVSS {item.cvss_score.toFixed(1)}
        </span>

        {/* Affected */}
        <span className="shrink-0 text-xs text-slate-400 w-24 text-right">
          {item.open_count} open / {item.total_count} total
        </span>
      </button>

      {expanded && (
        <div className="border-t border-slate-700/50 bg-slate-900/60 px-4 py-3 space-y-3">
          {/* Description */}
          <p className="text-xs text-slate-300 leading-relaxed">{item.description}</p>

          {/* Affected resources */}
          <div>
            <p className="text-xs font-medium text-slate-400 mb-2">
              Affected Resources ({item.resources.length})
            </p>
            <div className="space-y-1.5">
              {item.resources.map((r, idx) => (
                <div key={idx} className="flex items-center gap-3 text-xs bg-slate-800/50 rounded px-3 py-2">
                  <span className={cn("shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium capitalize",
                    SEV_COLOR[r.severity] ?? SEV_COLOR.low)}>
                    {r.severity}
                  </span>
                  <span className={cn("shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium",
                    r.status === "open" ? "bg-red-500/10 text-red-400" : "bg-green-500/10 text-green-400"
                  )}>
                    {r.status}
                  </span>
                  <span className="text-slate-400 shrink-0 text-[10px]">{r.resource_type}</span>
                  <span className="font-mono text-slate-300 truncate flex-1">{r.resource_arn || "—"}</span>
                  <span className="shrink-0 text-slate-500 text-[10px]">{r.region}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Dates */}
          {item.first_seen && (
            <p className="text-[11px] text-slate-500">
              First seen: {new Date(item.first_seen).toLocaleDateString()} ·
              Last seen: {item.last_seen ? new Date(item.last_seen).toLocaleDateString() : "—"}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function VulnsPage() {
  const { summary, isLoading: sumLoading } = useVulnSummary();
  const { items, isLoading: invLoading }   = useVulnInventory();

  const [sevFilter, setSevFilter]   = useState<string>("all");
  const [tierFilter, setTierFilter] = useState<string>("all");
  const [kevFilter, setKevFilter]   = useState<boolean>(false);
  const [search, setSearch]         = useState("");

  const isLoading = sumLoading || invLoading;

  const filtered = items.filter(item => {
    if (sevFilter !== "all" && item.severity !== sevFilter) return false;
    if (tierFilter !== "all" && item.risk_tier !== tierFilter) return false;
    if (kevFilter && !item.in_kev) return false;
    if (search && !item.cve_id.toLowerCase().includes(search.toLowerCase()) &&
        !item.description.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <main className="flex-1 overflow-y-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Vulnerability Management</h1>
        <p className="text-sm text-slate-400 mt-0.5">
          CVE inventory · EPSS exploitation probability · CISA KEV catalog
        </p>
      </div>

      {/* Summary cards */}
      {isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 rounded-xl bg-slate-800 animate-pulse" />
          ))}
        </div>
      ) : summary ? (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {/* Total CVEs */}
            <div className="rounded-xl bg-slate-800 border border-slate-700/50 p-4">
              <div className="flex items-center gap-2 mb-1">
                <Bug className="h-4 w-4 text-slate-400" />
                <span className="text-xs text-slate-400">Total CVEs</span>
              </div>
              <p className="text-2xl font-bold text-white">{summary.total_cves}</p>
              <p className="text-xs text-slate-500 mt-0.5">{summary.active_cves} with open findings</p>
            </div>

            {/* KEV Count */}
            <div className="rounded-xl bg-red-950/40 border border-red-500/20 p-4">
              <div className="flex items-center gap-2 mb-1">
                <ShieldAlert className="h-4 w-4 text-red-400" />
                <span className="text-xs text-red-400">CISA KEV</span>
              </div>
              <p className="text-2xl font-bold text-red-300">{summary.kev_count}</p>
              <p className="text-xs text-red-400/70 mt-0.5">Known exploited</p>
            </div>

            {/* Critical EPSS */}
            <div className="rounded-xl bg-orange-950/30 border border-orange-500/20 p-4">
              <div className="flex items-center gap-2 mb-1">
                <Zap className="h-4 w-4 text-orange-400" />
                <span className="text-xs text-orange-400">High EPSS (≥50%)</span>
              </div>
              <p className="text-2xl font-bold text-orange-300">{summary.critical_epss_count}</p>
              <p className="text-xs text-orange-400/70 mt-0.5">Likely exploited soon</p>
            </div>

            {/* Avg EPSS */}
            <div className="rounded-xl bg-slate-800 border border-slate-700/50 p-4">
              <div className="flex items-center gap-2 mb-1">
                <TrendingUp className="h-4 w-4 text-slate-400" />
                <span className="text-xs text-slate-400">Avg EPSS</span>
              </div>
              <p className="text-2xl font-bold text-white">{(summary.avg_epss * 100).toFixed(1)}%</p>
              <p className="text-xs text-slate-500 mt-0.5">Max {(summary.max_epss * 100).toFixed(1)}%</p>
            </div>
          </div>

          {/* Severity + EPSS distribution row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Severity breakdown */}
            <div className="rounded-xl bg-slate-800 border border-slate-700/50 p-4">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="h-4 w-4 text-slate-400" />
                <span className="text-sm font-medium text-white">CVEs by Severity</span>
              </div>
              <div className="space-y-2">
                {(["critical","high","medium","low"] as const).map(sev => {
                  const count = summary.severity_breakdown[sev] ?? 0;
                  const max   = Math.max(...Object.values(summary.severity_breakdown));
                  const pct   = max > 0 ? (count / max) * 100 : 0;
                  const bar   = sev === "critical" ? "bg-red-500" : sev === "high" ? "bg-orange-500" : sev === "medium" ? "bg-yellow-500" : "bg-blue-500";
                  return (
                    <div key={sev} className="flex items-center gap-3">
                      <span className="text-xs text-slate-400 capitalize w-14 shrink-0">{sev}</span>
                      <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
                        <div className={cn("h-full rounded-full", bar)} style={{ width: `${pct}%` }} />
                      </div>
                      <span className="text-xs text-slate-300 w-6 text-right">{count}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* EPSS distribution */}
            <div className="rounded-xl bg-slate-800 border border-slate-700/50 p-4">
              <div className="flex items-center gap-2 mb-3">
                <Activity className="h-4 w-4 text-slate-400" />
                <span className="text-sm font-medium text-white">EPSS Distribution</span>
                <span className="ml-auto text-[10px] text-slate-500">Exploitation probability</span>
              </div>
              <div className="space-y-2">
                {(["0.9+","0.5-0.9","0.1-0.5","<0.1"] as const).map(bucket => {
                  const count  = summary.epss_distribution[bucket] ?? 0;
                  const maxVal = Math.max(...Object.values(summary.epss_distribution));
                  const pct    = maxVal > 0 ? (count / maxVal) * 100 : 0;
                  const color  = bucket === "0.9+" ? "bg-red-500" : bucket === "0.5-0.9" ? "bg-orange-500" : bucket === "0.1-0.5" ? "bg-yellow-500" : "bg-slate-600";
                  const label  = bucket === "0.9+" ? "Critical (≥90%)" : bucket === "0.5-0.9" ? "High (50-90%)" : bucket === "0.1-0.5" ? "Medium (10-50%)" : "Low (<10%)";
                  return (
                    <div key={bucket} className="flex items-center gap-3">
                      <span className="text-xs text-slate-400 w-28 shrink-0">{label}</span>
                      <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
                        <div className={cn("h-full rounded-full", color)} style={{ width: `${pct}%` }} />
                      </div>
                      <span className="text-xs text-slate-300 w-6 text-right">{count}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </>
      ) : (
        <p className="text-sm text-red-400">Failed to load summary</p>
      )}

      {/* CVE Inventory */}
      <div className="rounded-xl bg-slate-800 border border-slate-700/50">
        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-3 px-4 py-3 border-b border-slate-700/50">
          <div className="flex items-center gap-2">
            <Filter className="h-3.5 w-3.5 text-slate-400" />
            <span className="text-xs text-slate-400 font-medium">Filter:</span>
          </div>

          {/* Search */}
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search CVE…"
            className="rounded-md border border-slate-600 bg-slate-700 px-2.5 py-1 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-blue-500 w-36"
          />

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
            <option value="low">Low</option>
          </select>

          {/* Risk tier filter */}
          <select
            value={tierFilter}
            onChange={e => setTierFilter(e.target.value)}
            className="rounded-md border border-slate-600 bg-slate-700 px-2 py-1 text-xs text-white focus:outline-none"
          >
            <option value="all">All risk tiers</option>
            <option value="imminent">Imminent</option>
            <option value="high">High</option>
            <option value="elevated">Elevated</option>
            <option value="moderate">Moderate</option>
          </select>

          {/* KEV toggle */}
          <button
            onClick={() => setKevFilter(!kevFilter)}
            className={cn(
              "rounded-md px-2.5 py-1 text-xs font-medium border transition-colors",
              kevFilter
                ? "bg-red-600/20 text-red-400 border-red-500/30"
                : "bg-slate-700 text-slate-400 border-slate-600 hover:text-white"
            )}
          >
            {kevFilter ? "KEV only ✓" : "KEV only"}
          </button>

          <span className="ml-auto text-xs text-slate-500">{filtered.length} CVEs</span>
        </div>

        {/* Column headers */}
        <div className="flex items-center gap-3 px-4 py-2 border-b border-slate-700/30 bg-slate-900/30">
          <span className="w-3.5 shrink-0" />
          <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider w-40 shrink-0">CVE ID</span>
          <span className="w-9 shrink-0" />
          <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider w-16 shrink-0">Severity</span>
          <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider flex-1">EPSS Score</span>
          <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider w-20 shrink-0">Risk Tier</span>
          <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider w-14 shrink-0 text-right">CVSS</span>
          <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider w-24 shrink-0 text-right">Findings</span>
        </div>

        {/* Rows */}
        <div className="p-3 space-y-1.5">
          {invLoading ? (
            [...Array(6)].map((_, i) => (
              <div key={i} className="h-12 rounded-lg bg-slate-700/50 animate-pulse" />
            ))
          ) : filtered.length === 0 ? (
            <p className="py-8 text-center text-sm text-slate-500">No CVEs match filters.</p>
          ) : (
            filtered.map(item => <CVERow key={item.cve_id} item={item} />)
          )}
        </div>
      </div>
    </main>
  );
}
