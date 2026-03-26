"use client";

import { useState } from "react";
import {
  Network, Zap, AlertTriangle, Search, Target, Shield,
  ChevronRight, Loader2,
} from "lucide-react";
import {
  useGraphSummary,
  useToxicCombinations,
  type AttackPathResult,
  type BlastRadiusResult,
} from "@/lib/hooks/use-graph-rag";
import { apiClient } from "@/lib/api-client";
import { Spinner } from "@/components/ui/spinner";

// ── Helpers ──────────────────────────────────────────────────────────────────

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(" ");
}

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: "bg-red-600 text-red-100",
  HIGH:     "bg-orange-600 text-orange-100",
  MEDIUM:   "bg-yellow-600 text-yellow-100",
  LOW:      "bg-slate-600 text-slate-200",
};

function riskColor(score: number) {
  if (score >= 80) return "text-red-400";
  if (score >= 60) return "text-orange-400";
  if (score >= 40) return "text-yellow-400";
  return "text-emerald-400";
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function GraphExplorerPage() {
  const { summary, isLoading: summaryLoading } = useGraphSummary();
  const { combinations, isLoading: toxicLoading } = useToxicCombinations();

  // Attack path state
  const [attackSource, setAttackSource] = useState("");
  const [attackPaths, setAttackPaths] = useState<AttackPathResult | null>(null);
  const [attackLoading, setAttackLoading] = useState(false);

  // Blast radius state
  const [blastArn, setBlastArn] = useState("");
  const [blastResult, setBlastResult] = useState<BlastRadiusResult | null>(null);
  const [blastLoading, setBlastLoading] = useState(false);

  async function handleFindPaths() {
    if (!attackSource.trim()) return;
    setAttackLoading(true);
    try {
      const result = await apiClient.get<AttackPathResult>(
        `/api/v1/graph/attack-paths?source=${encodeURIComponent(attackSource)}`
      );
      setAttackPaths(result);
    } catch (err) {
      console.error("Attack path search failed:", err);
    } finally {
      setAttackLoading(false);
    }
  }

  async function handleBlastRadius() {
    if (!blastArn.trim()) return;
    setBlastLoading(true);
    try {
      const result = await apiClient.get<BlastRadiusResult>(
        `/api/v1/graph/blast-radius?arn=${encodeURIComponent(blastArn)}`
      );
      setBlastResult(result);
    } catch (err) {
      console.error("Blast radius computation failed:", err);
    } finally {
      setBlastLoading(false);
    }
  }

  if (summaryLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-slate-900">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <header className="flex items-center gap-3 px-6 py-5 border-b border-slate-700">
        <Network className="h-6 w-6 text-blue-400" />
        <h1 className="text-xl font-bold tracking-tight">Graph Explorer</h1>
      </header>

      <div className="p-6 space-y-6">
        {/* ── Summary cards ──────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <SummaryCard
            icon={<Network className="h-5 w-5 text-blue-400" />}
            label="Total Nodes"
            value={summary?.total_nodes ?? 0}
          />
          <SummaryCard
            icon={<Zap className="h-5 w-5 text-purple-400" />}
            label="Total Edges"
            value={summary?.total_edges ?? 0}
          />
          <SummaryCard
            icon={<Shield className="h-5 w-5 text-emerald-400" />}
            label="Node Types"
            value={summary ? Object.keys(summary.nodes_by_type).length : 0}
          />
          <SummaryCard
            icon={<Target className="h-5 w-5 text-orange-400" />}
            label="Edge Types"
            value={summary ? Object.keys(summary.edges_by_type).length : 0}
          />
        </div>

        {/* ── Node / Edge type breakdowns ─────────────────────────────────── */}
        {summary && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <TypeBreakdownPanel title="Nodes by Type" data={summary.nodes_by_type} color="blue" />
            <TypeBreakdownPanel title="Edges by Type" data={summary.edges_by_type} color="purple" />
          </div>
        )}

        {/* ── Toxic Combinations ─────────────────────────────────────────── */}
        <div className="rounded-lg border border-slate-700 bg-slate-800 p-5">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-300 mb-4">
            <AlertTriangle className="h-4 w-4 text-red-400" />
            Toxic Combinations ({combinations.length})
          </h2>
          {toxicLoading ? (
            <div className="flex justify-center py-6"><Spinner /></div>
          ) : combinations.length === 0 ? (
            <p className="text-xs text-slate-500 text-center py-6">No toxic combinations detected.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {combinations.map((combo) => (
                <ToxicComboCard key={combo.resource_arn} combo={combo} />
              ))}
            </div>
          )}
        </div>

        {/* ── Two-column: Attack Paths + Blast Radius ─────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Attack Path Search */}
          <div className="rounded-lg border border-slate-700 bg-slate-800 p-5 space-y-4">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-300">
              <Search className="h-4 w-4 text-orange-400" />
              Attack Path Search
            </h2>
            <div className="flex gap-2">
              <input
                type="text"
                value={attackSource}
                onChange={(e) => setAttackSource(e.target.value)}
                placeholder="Source ARN (e.g. arn:aws:iam::123456:role/Admin)"
                onKeyDown={(e) => e.key === "Enter" && handleFindPaths()}
                className="flex-1 rounded-md border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
              />
              <button
                onClick={handleFindPaths}
                disabled={attackLoading || !attackSource.trim()}
                className={cn(
                  "flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors",
                  attackSource.trim() && !attackLoading
                    ? "bg-orange-600 text-white hover:bg-orange-500"
                    : "bg-slate-700 text-slate-400 cursor-not-allowed"
                )}
              >
                {attackLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                Find Paths
              </button>
            </div>

            {/* Attack path results */}
            {attackPaths && (
              <div className="space-y-3">
                <p className="text-xs text-slate-400">
                  Depth: {attackPaths.depth} | Nodes: {attackPaths.nodes.length} | Edges: {attackPaths.edges.length}
                </p>
                <div className="max-h-72 overflow-y-auto space-y-2 pr-1">
                  {attackPaths.nodes.map((node, i) => (
                    <div key={node.arn} className="flex items-center gap-2">
                      {i > 0 && (
                        <div className="flex items-center gap-1 text-[10px] text-slate-500">
                          <ChevronRight className="h-3 w-3" />
                          <span className="italic">
                            {attackPaths.edges[i - 1]?.type ?? ""}
                          </span>
                          <ChevronRight className="h-3 w-3" />
                        </div>
                      )}
                      <div className="rounded-md border border-slate-700 bg-slate-900 px-3 py-2 flex-1">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-medium text-white">{node.name}</span>
                          <span className={cn("text-xs font-bold", riskColor(node.risk_score))}>
                            {node.risk_score}
                          </span>
                        </div>
                        <p className="text-[10px] text-slate-500 font-mono truncate">{node.arn}</p>
                        <span className="text-[10px] text-slate-400">{node.type}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Blast Radius Search */}
          <div className="rounded-lg border border-slate-700 bg-slate-800 p-5 space-y-4">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-300">
              <Target className="h-4 w-4 text-red-400" />
              Blast Radius
            </h2>
            <div className="flex gap-2">
              <input
                type="text"
                value={blastArn}
                onChange={(e) => setBlastArn(e.target.value)}
                placeholder="Node ARN (e.g. arn:aws:ec2:us-east-1:123456:instance/i-abc)"
                onKeyDown={(e) => e.key === "Enter" && handleBlastRadius()}
                className="flex-1 rounded-md border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
              />
              <button
                onClick={handleBlastRadius}
                disabled={blastLoading || !blastArn.trim()}
                className={cn(
                  "flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors",
                  blastArn.trim() && !blastLoading
                    ? "bg-red-600 text-white hover:bg-red-500"
                    : "bg-slate-700 text-slate-400 cursor-not-allowed"
                )}
              >
                {blastLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Target className="h-4 w-4" />}
                Compute
              </button>
            </div>

            {/* Blast radius results */}
            {blastResult && (
              <div className="space-y-3">
                <div className="flex items-center gap-4">
                  <div className="rounded-lg border border-slate-700 bg-slate-900 px-4 py-3 text-center">
                    <p className="text-2xl font-bold text-red-400">{blastResult.reachable_count}</p>
                    <p className="text-[10px] text-slate-500">Reachable Nodes</p>
                  </div>
                  <div className="flex-1">
                    <p className="text-xs text-slate-400 mb-1">Origin</p>
                    <p className="text-xs font-mono text-white truncate">{blastResult.origin}</p>
                  </div>
                </div>
                <div className="max-h-60 overflow-y-auto space-y-1.5 pr-1">
                  {blastResult.reachable_nodes.map((node) => (
                    <div
                      key={node.arn}
                      className="flex items-center justify-between rounded-md border border-slate-700 bg-slate-900 px-3 py-2"
                    >
                      <div className="min-w-0 flex-1">
                        <span className="text-xs font-medium text-white">{node.name}</span>
                        <p className="text-[10px] text-slate-500 font-mono truncate">{node.arn}</p>
                      </div>
                      <span className="ml-2 rounded-full bg-slate-700 px-2 py-0.5 text-[10px] text-slate-300 shrink-0">
                        {node.type}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Summary card ────────────────────────────────────────────────────────────

function SummaryCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 px-5 py-4">
      <div className="flex items-center gap-3 mb-2">
        {icon}
        <span className="text-xs font-medium text-slate-400">{label}</span>
      </div>
      <p className="text-2xl font-bold text-white">{value.toLocaleString()}</p>
    </div>
  );
}

// ── Type breakdown panel ────────────────────────────────────────────────────

function TypeBreakdownPanel({ title, data, color }: { title: string; data: Record<string, number>; color: "blue" | "purple" }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  const max = entries.length > 0 ? entries[0][1] : 1;
  const barColor = color === "blue" ? "bg-blue-500" : "bg-purple-500";

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 p-4">
      <h3 className="text-xs font-semibold text-slate-300 mb-3">{title}</h3>
      <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
        {entries.map(([type, count]) => (
          <div key={type} className="flex items-center gap-3">
            <span className="text-xs text-slate-400 w-28 truncate shrink-0">{type}</span>
            <div className="flex-1 h-2 rounded-full bg-slate-700 overflow-hidden">
              <div
                className={cn("h-full rounded-full", barColor)}
                style={{ width: `${(count / max) * 100}%` }}
              />
            </div>
            <span className="text-xs text-slate-400 w-10 text-right">{count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Toxic combo card ────────────────────────────────────────────────────────

function ToxicComboCard({ combo }: { combo: import("@/lib/hooks/use-graph-rag").ToxicCombination }) {
  return (
    <div className="rounded-md border border-red-800/40 bg-slate-900 p-4 space-y-3">
      <div>
        <p className="text-sm font-medium text-white truncate">{combo.resource_name}</p>
        <p className="text-[10px] text-slate-500 font-mono truncate">{combo.resource_arn}</p>
        <span className="mt-1 inline-block rounded-full bg-slate-700 px-2 py-0.5 text-[10px] text-slate-300">
          {combo.resource_type}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <AlertTriangle className="h-3.5 w-3.5 text-red-400 shrink-0" />
        <span className="text-xs font-semibold text-red-400">{combo.finding_count} findings</span>
      </div>
      <div className="space-y-1.5">
        {combo.findings.slice(0, 4).map((f, i) => (
          <div key={i} className="flex items-center gap-2">
            <span className={cn("rounded-full px-1.5 py-0.5 text-[10px] font-medium", SEVERITY_COLORS[f.severity] ?? SEVERITY_COLORS.LOW)}>
              {f.severity}
            </span>
            <span className="text-xs text-slate-300 truncate">{f.title}</span>
          </div>
        ))}
        {combo.findings.length > 4 && (
          <p className="text-[10px] text-slate-500">+{combo.findings.length - 4} more</p>
        )}
      </div>
    </div>
  );
}
