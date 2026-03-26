"use client";

import { useState, useMemo } from "react";
import {
  Clock, TrendingUp, DollarSign, BarChart3, ChevronDown,
  ArrowUpDown, Atom, AlertTriangle,
} from "lucide-react";
import {
  useDomainTrends,
  useCostAnalysis,
  type DomainTrend,
} from "@/lib/hooks/use-audit-trail";
import { useSimulations } from "@/lib/hooks/use-simulations";
import { Spinner } from "@/components/ui/spinner";

// ── Helpers ──────────────────────────────────────────────────────────────────

function fmtCost(usd: number) {
  return `$${usd.toFixed(4)}`;
}

function fmtPct(v: number) {
  return `${(v * 100).toFixed(1)}%`;
}

function confColor(v: number) {
  if (v >= 0.85) return "text-emerald-400";
  if (v >= 0.6) return "text-yellow-400";
  return "text-red-400";
}

type SortKey = keyof DomainTrend;

// ── Summary Card ─────────────────────────────────────────────────────────────

function SummaryCard({
  label, value, sub, icon: Icon, iconColor,
}: {
  label: string; value: string; sub?: string; icon: typeof Clock; iconColor: string;
}) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800/60 p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-slate-400">{label}</span>
        <Icon className={`h-4 w-4 ${iconColor}`} />
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function SessionHistoryPage() {
  const { runs, isLoading: runsLoading } = useSimulations();
  const { trends, isLoading: trendsLoading } = useDomainTrends();
  const [costDays, setCostDays] = useState(30);
  const { costs, isLoading: costsLoading } = useCostAnalysis(costDays);
  const [sortKey, setSortKey] = useState<SortKey>("run_count");
  const [sortAsc, setSortAsc] = useState(false);
  const [compareA, setCompareA] = useState("");
  const [compareB, setCompareB] = useState("");

  const completedRuns = (runs ?? []).filter((r: any) => r.status === "completed");

  // Summary stats
  const totalRuns = completedRuns.length;
  const avgConf = totalRuns > 0
    ? completedRuns.reduce((s: number, r: any) => s + r.confidence_score, 0) / totalRuns
    : 0;
  const totalCost = completedRuns.reduce((s: number, r: any) => s + r.total_cost_usd, 0);
  const domainCounts: Record<string, number> = {};
  completedRuns.forEach((r: any) => { domainCounts[r.domain] = (domainCounts[r.domain] || 0) + 1; });
  const topDomain = Object.entries(domainCounts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "--";

  // Sorted trends
  const sortedTrends = useMemo(() => {
    const copy = [...trends];
    copy.sort((a, b) => {
      const aVal = a[sortKey] as number;
      const bVal = b[sortKey] as number;
      return sortAsc ? aVal - bVal : bVal - aVal;
    });
    return copy;
  }, [trends, sortKey, sortAsc]);

  function handleSort(key: SortKey) {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(false); }
  }

  // Cost chart max
  const maxDailyCost = costs ? Math.max(...costs.daily_costs.map((d) => d.cost), 0.001) : 1;

  // Run comparison
  const runA = completedRuns.find((r: any) => r.id === compareA);
  const runB = completedRuns.find((r: any) => r.id === compareB);

  const isLoading = runsLoading || trendsLoading;

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Clock className="h-6 w-6 text-blue-400" />
        <h1 className="text-xl font-semibold text-white">Session History &amp; Analytics</h1>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryCard
          label="Total Simulations"
          value={totalRuns.toString()}
          sub="Completed runs"
          icon={Atom}
          iconColor="text-blue-400"
        />
        <SummaryCard
          label="Avg Confidence"
          value={fmtPct(avgConf)}
          sub="Across all runs"
          icon={TrendingUp}
          iconColor="text-emerald-400"
        />
        <SummaryCard
          label="Total Cost"
          value={fmtCost(totalCost)}
          sub="All simulation runs"
          icon={DollarSign}
          iconColor="text-yellow-400"
        />
        <SummaryCard
          label="Top Domain"
          value={topDomain}
          sub={domainCounts[topDomain] ? `${domainCounts[topDomain]} runs` : undefined}
          icon={BarChart3}
          iconColor="text-purple-400"
        />
      </div>

      {/* Domain Trends Table */}
      <section className="rounded-xl border border-slate-700 bg-slate-800/40 overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-700">
          <h2 className="text-sm font-semibold text-white">Domain Trends</h2>
        </div>
        {trends.length === 0 ? (
          <div className="py-12 text-center text-sm text-slate-500">No trend data available</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700 text-left">
                  {([
                    ["domain", "Domain"],
                    ["run_count", "Runs"],
                    ["avg_confidence", "Avg Conf"],
                    ["best_confidence", "Best"],
                    ["worst_confidence", "Worst"],
                    ["avg_cost", "Avg Cost"],
                    ["total_cost", "Total Cost"],
                  ] as [SortKey, string][]).map(([key, label]) => (
                    <th
                      key={key}
                      onClick={() => handleSort(key)}
                      className="cursor-pointer px-5 py-3 text-xs font-medium text-slate-400 hover:text-white transition-colors select-none"
                    >
                      <span className="inline-flex items-center gap-1">
                        {label}
                        <ArrowUpDown className="h-3 w-3" />
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sortedTrends.map((t) => (
                  <tr key={t.domain} className="border-b border-slate-700/40 hover:bg-slate-800/60 transition-colors">
                    <td className="px-5 py-3 font-medium text-white">{t.domain}</td>
                    <td className="px-5 py-3 text-slate-300">{t.run_count}</td>
                    <td className={`px-5 py-3 font-medium ${confColor(t.avg_confidence)}`}>
                      {fmtPct(t.avg_confidence)}
                    </td>
                    <td className={`px-5 py-3 ${confColor(t.best_confidence)}`}>
                      {fmtPct(t.best_confidence)}
                    </td>
                    <td className={`px-5 py-3 ${confColor(t.worst_confidence)}`}>
                      {fmtPct(t.worst_confidence)}
                    </td>
                    <td className="px-5 py-3 text-slate-300">{fmtCost(t.avg_cost)}</td>
                    <td className="px-5 py-3 text-slate-300">{fmtCost(t.total_cost)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Cost Analysis */}
      <section className="rounded-xl border border-slate-700 bg-slate-800/40">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
          <h2 className="text-sm font-semibold text-white">Cost Analysis</h2>
          <select
            value={costDays}
            onChange={(e) => setCostDays(Number(e.target.value))}
            className="appearance-none rounded-lg border border-slate-600 bg-slate-700 px-3 py-1.5 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
          >
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
        </div>

        {costsLoading ? (
          <div className="flex justify-center py-12"><Spinner /></div>
        ) : !costs ? (
          <div className="py-12 text-center text-sm text-slate-500">No cost data available</div>
        ) : (
          <div className="p-5 space-y-5">
            {/* Budget bar */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-slate-400">Budget Utilization</span>
                <span className="text-xs font-medium text-slate-200">
                  {(costs.budget_used_pct * 100).toFixed(1)}%
                </span>
              </div>
              <div className="h-3 w-full rounded-full bg-slate-700 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    costs.budget_used_pct > 0.9 ? "bg-red-500" : costs.budget_used_pct > 0.7 ? "bg-yellow-500" : "bg-emerald-500"
                  }`}
                  style={{ width: `${Math.min(costs.budget_used_pct * 100, 100)}%` }}
                />
              </div>
            </div>

            {/* Daily cost chart (div-based) */}
            <div>
              <p className="text-xs text-slate-400 mb-3">Daily Costs</p>
              <div className="flex items-end gap-1 h-32">
                {costs.daily_costs.map((d) => (
                  <div key={d.date} className="flex-1 flex flex-col items-center gap-1 group relative">
                    <div
                      className="w-full rounded-t bg-blue-500/80 hover:bg-blue-400 transition-colors min-h-[2px]"
                      style={{ height: `${(d.cost / maxDailyCost) * 100}%` }}
                    />
                    {/* Tooltip */}
                    <div className="absolute bottom-full mb-2 hidden group-hover:block rounded bg-slate-900 border border-slate-600 px-2 py-1 text-[10px] text-slate-200 whitespace-nowrap z-10">
                      {d.date}: {fmtCost(d.cost)} ({d.runs} runs)
                    </div>
                  </div>
                ))}
              </div>
              {costs.daily_costs.length > 0 && (
                <div className="flex justify-between mt-1">
                  <span className="text-[10px] text-slate-600">{costs.daily_costs[0]?.date}</span>
                  <span className="text-[10px] text-slate-600">
                    {costs.daily_costs[costs.daily_costs.length - 1]?.date}
                  </span>
                </div>
              )}
            </div>

            {/* Domain cost breakdown */}
            {Object.keys(costs.by_domain).length > 0 && (
              <div>
                <p className="text-xs text-slate-400 mb-2">Cost by Domain</p>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
                  {Object.entries(costs.by_domain)
                    .sort((a, b) => b[1] - a[1])
                    .map(([domain, cost]) => (
                      <div
                        key={domain}
                        className="rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-2"
                      >
                        <p className="text-xs font-medium text-white truncate">{domain}</p>
                        <p className="text-sm font-bold text-slate-200">{fmtCost(cost)}</p>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        )}
      </section>

      {/* Run Comparison */}
      <section className="rounded-xl border border-slate-700 bg-slate-800/40">
        <div className="px-5 py-4 border-b border-slate-700">
          <h2 className="text-sm font-semibold text-white">Run Comparison</h2>
        </div>
        <div className="p-5 space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row">
            {/* Run A selector */}
            <div className="relative flex-1">
              <select
                value={compareA}
                onChange={(e) => setCompareA(e.target.value)}
                className="w-full appearance-none rounded-lg border border-slate-700 bg-slate-800 px-4 py-2.5 pr-10 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
              >
                <option value="">Run A...</option>
                {completedRuns.map((r: any) => (
                  <option key={r.id} value={r.id}>
                    {r.domain} — {new Date(r.created_at).toLocaleDateString()}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-3 h-4 w-4 text-slate-500" />
            </div>

            <span className="self-center text-slate-500 text-sm font-medium">vs</span>

            {/* Run B selector */}
            <div className="relative flex-1">
              <select
                value={compareB}
                onChange={(e) => setCompareB(e.target.value)}
                className="w-full appearance-none rounded-lg border border-slate-700 bg-slate-800 px-4 py-2.5 pr-10 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
              >
                <option value="">Run B...</option>
                {completedRuns.map((r: any) => (
                  <option key={r.id} value={r.id}>
                    {r.domain} — {new Date(r.created_at).toLocaleDateString()}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-3 h-4 w-4 text-slate-500" />
            </div>
          </div>

          {runA && runB ? (
            <div className="grid grid-cols-3 gap-4 text-center">
              {/* Header row */}
              <div className="text-xs font-medium text-slate-400">Metric</div>
              <div className="text-xs font-medium text-blue-400">Run A</div>
              <div className="text-xs font-medium text-purple-400">Run B</div>

              {/* Domain */}
              <div className="text-sm text-slate-400">Domain</div>
              <div className="text-sm font-medium text-white">{runA.domain}</div>
              <div className="text-sm font-medium text-white">{runB.domain}</div>

              {/* Confidence */}
              <div className="text-sm text-slate-400">Confidence</div>
              <div className={`text-sm font-medium ${confColor(runA.confidence_score)}`}>
                {fmtPct(runA.confidence_score)}
              </div>
              <div className={`text-sm font-medium ${confColor(runB.confidence_score)}`}>
                {fmtPct(runB.confidence_score)}
              </div>

              {/* Gates */}
              <div className="text-sm text-slate-400">Gates</div>
              <div className="text-sm text-slate-200">
                {runA.gates_passed}/{runA.gates_total}
              </div>
              <div className="text-sm text-slate-200">
                {runB.gates_passed}/{runB.gates_total}
              </div>

              {/* Cost */}
              <div className="text-sm text-slate-400">Cost</div>
              <div className="text-sm text-slate-200">{fmtCost(runA.total_cost_usd)}</div>
              <div className="text-sm text-slate-200">{fmtCost(runB.total_cost_usd)}</div>

              {/* Agents */}
              <div className="text-sm text-slate-400">Agents</div>
              <div className="text-sm text-slate-200">{runA.agent_count}</div>
              <div className="text-sm text-slate-200">{runB.agent_count}</div>

              {/* Duration */}
              <div className="text-sm text-slate-400">Duration</div>
              <div className="text-sm text-slate-200">
                {runA.duration_seconds ? `${runA.duration_seconds.toFixed(1)}s` : "--"}
              </div>
              <div className="text-sm text-slate-200">
                {runB.duration_seconds ? `${runB.duration_seconds.toFixed(1)}s` : "--"}
              </div>
            </div>
          ) : (
            <div className="py-8 text-center text-sm text-slate-500">
              Select two completed runs to compare
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
