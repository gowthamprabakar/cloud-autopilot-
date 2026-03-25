"use client";

import { useState, useMemo } from "react";
import {
  Route,
  Target,
  Zap,
  ArrowRight,
  ChevronDown,
  ChevronRight,
  Shield,
  Globe,
} from "lucide-react";
import {
  useAttackPathSummary,
  useAttackPaths,
  useBlastRadius,
  type AttackPathNode,
} from "@/lib/hooks/use-attack-paths";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function severityColor(severity: string) {
  switch (severity.toLowerCase()) {
    case "critical":
      return "bg-red-500/20 text-red-400 border-red-500/30";
    case "high":
      return "bg-orange-500/20 text-orange-400 border-orange-500/30";
    case "medium":
      return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30";
    case "low":
      return "bg-blue-500/20 text-blue-400 border-blue-500/30";
    default:
      return "bg-slate-500/20 text-slate-400 border-slate-500/30";
  }
}

function riskColor(score: number) {
  if (score >= 80) return "text-red-400";
  if (score >= 60) return "text-orange-400";
  if (score >= 40) return "text-yellow-400";
  return "text-blue-400";
}

function riskBarColor(score: number) {
  if (score >= 80) return "bg-red-500";
  if (score >= 60) return "bg-orange-500";
  if (score >= 40) return "bg-yellow-500";
  return "bg-blue-500";
}

function typeColor(type: string) {
  switch (type.toLowerCase()) {
    case "ec2":
    case "instance":
      return "bg-purple-500/20 text-purple-400";
    case "s3":
    case "bucket":
      return "bg-green-500/20 text-green-400";
    case "iam":
    case "role":
    case "user":
      return "bg-yellow-500/20 text-yellow-400";
    case "lambda":
    case "function":
      return "bg-orange-500/20 text-orange-400";
    case "rds":
    case "database":
      return "bg-blue-500/20 text-blue-400";
    default:
      return "bg-slate-500/20 text-slate-400";
  }
}

/* ------------------------------------------------------------------ */
/*  Summary Card                                                       */
/* ------------------------------------------------------------------ */

function SummaryCard({
  label,
  value,
  icon: Icon,
  accent = "text-blue-400",
}: {
  label: string;
  value: string | number;
  icon: React.ElementType;
  accent?: string;
}) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800/60 p-5">
      <div className="flex items-center gap-3 mb-3">
        <div className={`rounded-lg bg-slate-700/50 p-2 ${accent}`}>
          <Icon className="h-4 w-4" />
        </div>
        <span className="text-xs font-medium text-slate-400 uppercase tracking-wide">
          {label}
        </span>
      </div>
      <p className={`text-2xl font-bold ${accent}`}>{value}</p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Attack Path Card                                                   */
/* ------------------------------------------------------------------ */

function AttackPathCard({
  path,
}: {
  path: ReturnType<typeof useAttackPaths>["paths"][number];
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800/60 overflow-hidden">
      {/* Header row */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-4 px-5 py-4 text-left hover:bg-slate-700/30 transition-colors"
      >
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-slate-400 shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-slate-400 shrink-0" />
        )}

        {/* Source -> Target */}
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <span className="text-sm font-medium text-white truncate">
            {path.source_name}
          </span>
          <ArrowRight className="h-3.5 w-3.5 text-slate-500 shrink-0" />
          <span className="text-sm font-medium text-white truncate">
            {path.target_name}
          </span>
        </div>

        {/* Metadata */}
        <div className="flex items-center gap-3 shrink-0">
          <span className="text-xs text-slate-400">
            {path.length} {path.length === 1 ? "hop" : "hops"}
          </span>

          {/* Risk gauge */}
          <div className="flex items-center gap-2">
            <div className="w-16 h-1.5 rounded-full bg-slate-700 overflow-hidden">
              <div
                className={`h-full rounded-full ${riskBarColor(path.total_risk)}`}
                style={{ width: `${Math.min(path.total_risk, 100)}%` }}
              />
            </div>
            <span className={`text-xs font-semibold ${riskColor(path.total_risk)}`}>
              {path.total_risk}
            </span>
          </div>

          {/* Severity badge */}
          <span
            className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full border ${severityColor(
              path.severity
            )}`}
          >
            {path.severity}
          </span>
        </div>
      </button>

      {/* Expanded chain visualization */}
      {expanded && (
        <div className="border-t border-slate-700 px-5 py-4 bg-slate-900/40">
          <p className="text-[10px] font-medium text-slate-500 uppercase tracking-wider mb-3">
            Attack Chain
          </p>
          <div className="flex items-center gap-1 overflow-x-auto pb-2">
            {path.nodes.map((node, idx) => (
              <div key={node.id} className="flex items-center gap-1 shrink-0">
                {/* Node pill */}
                <div className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 min-w-[120px]">
                  <p className="text-xs font-medium text-white truncate">
                    {node.name}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <span
                      className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${typeColor(
                        node.type
                      )}`}
                    >
                      {node.type}
                    </span>
                    <span className={`text-[10px] font-semibold ${riskColor(node.risk_score)}`}>
                      {node.risk_score}
                    </span>
                  </div>
                </div>

                {/* Arrow between nodes */}
                {idx < path.nodes.length - 1 && (
                  <ArrowRight className="h-3.5 w-3.5 text-slate-500 shrink-0" />
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Blast Radius Tab                                                   */
/* ------------------------------------------------------------------ */

function BlastRadiusTab({
  allNodes,
}: {
  allNodes: AttackPathNode[];
}) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const { blastRadius, isLoading } = useBlastRadius(selectedNodeId);

  return (
    <div className="space-y-6">
      {/* Node selector */}
      <div className="rounded-xl border border-slate-700 bg-slate-800/60 p-5">
        <label className="block text-xs font-medium text-slate-400 uppercase tracking-wide mb-2">
          Select Origin Node
        </label>
        <select
          value={selectedNodeId ?? ""}
          onChange={(e) => setSelectedNodeId(e.target.value || null)}
          className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Choose a node...</option>
          {allNodes.map((n) => (
            <option key={n.id} value={n.id}>
              {n.name} ({n.type})
            </option>
          ))}
        </select>
      </div>

      {/* Loading */}
      {selectedNodeId && isLoading && (
        <div className="text-center py-12 text-slate-400 text-sm">
          Loading blast radius...
        </div>
      )}

      {/* Results */}
      {blastRadius && (
        <div className="space-y-4">
          {/* Origin card */}
          <div className="rounded-xl border border-blue-500/30 bg-blue-500/5 p-5">
            <div className="flex items-center gap-3 mb-2">
              <Target className="h-4 w-4 text-blue-400" />
              <span className="text-xs font-medium text-blue-400 uppercase tracking-wide">
                Origin Node
              </span>
            </div>
            <p className="text-lg font-semibold text-white">
              {blastRadius.origin.name}
            </p>
            <div className="flex items-center gap-3 mt-2">
              <span
                className={`text-xs font-medium px-2 py-0.5 rounded ${typeColor(
                  blastRadius.origin.type
                )}`}
              >
                {blastRadius.origin.type}
              </span>
              <span className="text-xs text-slate-400">
                {blastRadius.origin.region}
              </span>
              {blastRadius.origin.is_internet_facing && (
                <span className="flex items-center gap-1 text-xs text-orange-400">
                  <Globe className="h-3 w-3" /> Internet Facing
                </span>
              )}
            </div>
          </div>

          {/* Stats row */}
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-xl border border-slate-700 bg-slate-800/60 p-4">
              <p className="text-xs text-slate-400 mb-1">Total Reachable</p>
              <p className="text-xl font-bold text-orange-400">
                {blastRadius.total_reachable}
              </p>
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-800/60 p-4">
              <p className="text-xs text-slate-400 mb-1">Max Depth</p>
              <p className="text-xl font-bold text-purple-400">
                {blastRadius.max_depth}
              </p>
            </div>
          </div>

          {/* Reachable nodes */}
          <div>
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-3">
              Reachable Nodes ({blastRadius.reachable_nodes.length})
            </p>
            <div className="grid gap-2">
              {blastRadius.reachable_nodes.map((node) => (
                <div
                  key={node.id}
                  className="rounded-lg border border-slate-700 bg-slate-800/60 px-4 py-3 flex items-center justify-between"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="text-sm font-medium text-white truncate">
                      {node.name}
                    </span>
                    <span
                      className={`text-[10px] font-medium px-1.5 py-0.5 rounded shrink-0 ${typeColor(
                        node.type
                      )}`}
                    >
                      {node.type}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-xs text-slate-400">{node.region}</span>
                    <span
                      className={`text-xs font-semibold ${riskColor(node.risk_score)}`}
                    >
                      {node.risk_score}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!selectedNodeId && (
        <div className="text-center py-16">
          <Target className="h-10 w-10 text-slate-600 mx-auto mb-3" />
          <p className="text-sm text-slate-400">
            Select a node above to analyze its blast radius
          </p>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Page                                                          */
/* ------------------------------------------------------------------ */

export default function AttackPathsPage() {
  const [activeTab, setActiveTab] = useState<"paths" | "blast">("paths");
  const { summary, isLoading: summaryLoading } = useAttackPathSummary();
  const { paths, isLoading: pathsLoading } = useAttackPaths();

  // Deduplicate nodes across all paths for the blast radius selector
  const allNodes = useMemo(() => {
    const map = new Map<string, AttackPathNode>();
    paths.forEach((p) => p.nodes.forEach((n) => map.set(n.id, n)));
    return Array.from(map.values()).sort((a, b) => a.name.localeCompare(b.name));
  }, [paths]);

  const tabs = [
    { key: "paths" as const, label: "Attack Paths", icon: Route },
    { key: "blast" as const, label: "Blast Radius", icon: Target },
  ];

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <div className="rounded-lg bg-red-500/10 p-2">
            <Route className="h-5 w-5 text-red-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold">Attack Path Analysis</h1>
            <p className="text-sm text-slate-400">
              Visualize and assess potential attack chains across your cloud infrastructure
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 bg-slate-800/60 rounded-lg p-1 w-fit border border-slate-700">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? "bg-blue-600 text-white"
                  : "text-slate-400 hover:text-white hover:bg-slate-700/50"
              }`}
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* ---- Attack Paths Tab ---- */}
        {activeTab === "paths" && (
          <div className="space-y-6">
            {/* Summary cards */}
            {summaryLoading ? (
              <div className="grid grid-cols-4 gap-4">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div
                    key={i}
                    className="h-28 rounded-xl border border-slate-700 bg-slate-800/40 animate-pulse"
                  />
                ))}
              </div>
            ) : summary ? (
              <div className="grid grid-cols-4 gap-4">
                <SummaryCard
                  label="Total Paths"
                  value={summary.total_paths}
                  icon={Route}
                  accent="text-blue-400"
                />
                <SummaryCard
                  label="Critical Paths"
                  value={summary.critical_paths}
                  icon={Zap}
                  accent="text-red-400"
                />
                <SummaryCard
                  label="Avg Risk Score"
                  value={summary.avg_risk.toFixed(1)}
                  icon={Shield}
                  accent="text-orange-400"
                />
                <SummaryCard
                  label="Max Chain Length"
                  value={summary.max_chain_length}
                  icon={ArrowRight}
                  accent="text-purple-400"
                />
              </div>
            ) : null}

            {/* Path list */}
            {pathsLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div
                    key={i}
                    className="h-16 rounded-xl border border-slate-700 bg-slate-800/40 animate-pulse"
                  />
                ))}
              </div>
            ) : paths.length === 0 ? (
              <div className="text-center py-16">
                <Route className="h-10 w-10 text-slate-600 mx-auto mb-3" />
                <p className="text-sm text-slate-400">
                  No attack paths detected
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-xs font-medium text-slate-400 uppercase tracking-wide">
                  {paths.length} Attack {paths.length === 1 ? "Path" : "Paths"} Detected
                </p>
                {paths.map((path) => (
                  <AttackPathCard key={path.id} path={path} />
                ))}
              </div>
            )}
          </div>
        )}

        {/* ---- Blast Radius Tab ---- */}
        {activeTab === "blast" && <BlastRadiusTab allNodes={allNodes} />}
      </div>
    </div>
  );
}
