"use client";

import { useState } from "react";
import {
  Brain, Database, BarChart3, Clock, ChevronDown, ChevronRight,
  Loader2, RefreshCw, Sparkles, Eye,
} from "lucide-react";
import {
  useAgentMemory,
  useAgentMemoryRecall,
  triggerLearn,
  type MemoryEntry,
} from "@/lib/hooks/use-agent-memory";
import { apiClient } from "@/lib/api-client";
import { Spinner } from "@/components/ui/spinner";

// ── Constants ────────────────────────────────────────────────────────────────

const AGENT_TYPES = [
  { id: "RECON-01",     name: "Recon Agent" },
  { id: "SCANNER-01",   name: "Scanner Agent" },
  { id: "EXPLOIT-01",   name: "Exploit Agent" },
  { id: "LATERAL-01",   name: "Lateral Movement" },
  { id: "PERSIST-01",   name: "Persistence Agent" },
  { id: "EXFIL-01",     name: "Exfil Agent" },
  { id: "DEFENSE-01",   name: "Defense Evasion" },
  { id: "REPORT-01",    name: "Report Agent" },
  { id: "VALIDATOR-01", name: "Validator Agent" },
  { id: "ORCHESTRATOR", name: "Orchestrator" },
  { id: "CSPM-01",      name: "CSPM Agent" },
  { id: "CIEM-01",      name: "CIEM Agent" },
  { id: "CDR-01",       name: "CDR Agent" },
  { id: "VULN-01",      name: "Vuln Agent" },
  { id: "IaC-01",       name: "IaC Scanner" },
] as const;

const MEMORY_TYPES = ["working", "episodic", "semantic", "procedural"] as const;

const TYPE_COLORS: Record<string, string> = {
  working:    "bg-blue-600 text-blue-100",
  episodic:   "bg-purple-600 text-purple-100",
  semantic:   "bg-emerald-600 text-emerald-100",
  procedural: "bg-orange-600 text-orange-100",
};

// ── Helpers ──────────────────────────────────────────────────────────────────

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(" ");
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function truncate(val: any, maxLen = 80): string {
  const s = typeof val === "string" ? val : JSON.stringify(val);
  return s.length > maxLen ? s.slice(0, maxLen) + "..." : s;
}

function relevanceBarColor(score: number) {
  if (score >= 0.8) return "bg-emerald-500";
  if (score >= 0.5) return "bg-yellow-500";
  if (score >= 0.3) return "bg-orange-500";
  return "bg-red-500";
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function AgentMemoryPage() {
  const [selectedAgent, setSelectedAgent] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [decaying, setDecaying] = useState(false);
  const [learning, setLearning] = useState(false);
  const [learnRunId, setLearnRunId] = useState("");

  const { summary, isLoading: summaryLoading, mutate } = useAgentMemory(selectedAgent);
  const { memories, isLoading: memoriesLoading } = useAgentMemoryRecall(
    selectedAgent,
    typeFilter || undefined
  );

  async function handleDecay() {
    if (!selectedAgent) return;
    setDecaying(true);
    try {
      await apiClient.post(`/api/v1/memory/${selectedAgent}/decay`, {});
      await mutate();
    } catch (err) {
      console.error("Decay failed:", err);
    } finally {
      setDecaying(false);
    }
  }

  async function handleLearn() {
    if (!learnRunId.trim()) return;
    setLearning(true);
    try {
      await triggerLearn(learnRunId);
      await mutate();
    } catch (err) {
      console.error("Learn failed:", err);
    } finally {
      setLearning(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <header className="flex items-center justify-between px-6 py-5 border-b border-slate-700">
        <div className="flex items-center gap-3">
          <Brain className="h-6 w-6 text-purple-400" />
          <h1 className="text-xl font-bold tracking-tight">Agent Memory Explorer</h1>
        </div>

        {/* Agent selector */}
        <div className="flex items-center gap-3">
          <select
            value={selectedAgent}
            onChange={(e) => {
              setSelectedAgent(e.target.value);
              setExpandedRow(null);
            }}
            className="rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
          >
            <option value="">-- select agent --</option>
            {AGENT_TYPES.map((a) => (
              <option key={a.id} value={a.id}>{a.id} — {a.name}</option>
            ))}
          </select>
        </div>
      </header>

      <div className="p-6 space-y-6">
        {!selectedAgent ? (
          <div className="rounded-lg border border-slate-700 bg-slate-800 p-12 text-center">
            <Brain className="h-10 w-10 text-slate-600 mx-auto mb-3" />
            <p className="text-sm text-slate-400">Select an agent to explore its memory.</p>
          </div>
        ) : summaryLoading ? (
          <div className="flex justify-center py-12"><Spinner /></div>
        ) : (
          <>
            {/* ── Summary cards ────────────────────────────────────────────── */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard
                icon={<Database className="h-5 w-5 text-blue-400" />}
                label="Total Memories"
                value={summary?.total_memories ?? 0}
              />
              <StatCard
                icon={<BarChart3 className="h-5 w-5 text-emerald-400" />}
                label="Avg Relevance"
                value={summary ? `${(summary.avg_relevance * 100).toFixed(1)}%` : "—"}
              />
              <StatCard
                icon={<Clock className="h-5 w-5 text-yellow-400" />}
                label="Oldest"
                value={summary?.oldest ? timeAgo(summary.oldest) : "—"}
              />
              <StatCard
                icon={<Clock className="h-5 w-5 text-purple-400" />}
                label="Newest"
                value={summary?.newest ? timeAgo(summary.newest) : "—"}
              />
            </div>

            {/* ── Type breakdown ───────────────────────────────────────────── */}
            {summary?.by_type && (
              <div className="rounded-lg border border-slate-700 bg-slate-800 p-4">
                <h3 className="text-xs font-semibold text-slate-300 mb-3">Memory by Type</h3>
                <div className="flex flex-wrap gap-3">
                  {Object.entries(summary.by_type).map(([type, count]) => (
                    <div key={type} className="flex items-center gap-2 rounded-md border border-slate-700 bg-slate-900 px-3 py-2">
                      <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-medium", TYPE_COLORS[type] ?? "bg-slate-600 text-slate-200")}>
                        {type}
                      </span>
                      <span className="text-sm font-semibold text-white">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ── Actions row ──────────────────────────────────────────────── */}
            <div className="flex flex-wrap items-center gap-3">
              <button
                onClick={handleDecay}
                disabled={decaying}
                className={cn(
                  "flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors",
                  decaying
                    ? "bg-slate-700 text-slate-400 cursor-not-allowed"
                    : "bg-yellow-600 text-white hover:bg-yellow-500"
                )}
              >
                {decaying ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                Decay Relevance
              </button>

              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={learnRunId}
                  onChange={(e) => setLearnRunId(e.target.value)}
                  placeholder="Simulation Run ID"
                  className="rounded-md border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none w-56"
                />
                <button
                  onClick={handleLearn}
                  disabled={learning || !learnRunId.trim()}
                  className={cn(
                    "flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors",
                    learnRunId.trim() && !learning
                      ? "bg-purple-600 text-white hover:bg-purple-500"
                      : "bg-slate-700 text-slate-400 cursor-not-allowed"
                  )}
                >
                  {learning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                  Learn from Simulation
                </button>
              </div>
            </div>

            {/* ── Memory table ─────────────────────────────────────────────── */}
            <div className="rounded-lg border border-slate-700 bg-slate-800 overflow-hidden">
              <div className="flex items-center justify-between px-5 py-3 border-b border-slate-700">
                <h3 className="text-sm font-semibold text-slate-300">
                  Memories ({memories.length})
                </h3>
                <select
                  value={typeFilter}
                  onChange={(e) => setTypeFilter(e.target.value)}
                  className="rounded-md border border-slate-600 bg-slate-900 px-2 py-1 text-xs text-white focus:border-blue-500 focus:outline-none"
                >
                  <option value="">All Types</option>
                  {MEMORY_TYPES.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>

              {memoriesLoading ? (
                <div className="flex justify-center py-8"><Spinner /></div>
              ) : memories.length === 0 ? (
                <div className="text-center py-8">
                  <Database className="h-8 w-8 text-slate-600 mx-auto mb-2" />
                  <p className="text-xs text-slate-500">No memories found.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-700 text-left text-xs text-slate-500">
                        <th className="px-5 py-2.5 font-medium w-8" />
                        <th className="px-5 py-2.5 font-medium">Type</th>
                        <th className="px-5 py-2.5 font-medium">Key</th>
                        <th className="px-5 py-2.5 font-medium">Value</th>
                        <th className="px-5 py-2.5 font-medium">Relevance</th>
                        <th className="px-5 py-2.5 font-medium">Accesses</th>
                        <th className="px-5 py-2.5 font-medium">Age</th>
                      </tr>
                    </thead>
                    <tbody>
                      {memories.map((mem) => (
                        <MemoryRow
                          key={mem.id}
                          mem={mem}
                          expanded={expandedRow === mem.id}
                          onToggle={() => setExpandedRow(expandedRow === mem.id ? null : mem.id)}
                        />
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ── Stat card ───────────────────────────────────────────────────────────────

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 px-5 py-4">
      <div className="flex items-center gap-3 mb-2">
        {icon}
        <span className="text-xs font-medium text-slate-400">{label}</span>
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
    </div>
  );
}

// ── Memory row ──────────────────────────────────────────────────────────────

function MemoryRow({
  mem,
  expanded,
  onToggle,
}: {
  mem: MemoryEntry;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <>
      <tr
        onClick={onToggle}
        className="border-b border-slate-700/50 cursor-pointer hover:bg-slate-700/30 transition-colors"
      >
        <td className="px-5 py-3">
          {expanded
            ? <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
            : <ChevronRight className="h-3.5 w-3.5 text-slate-400" />}
        </td>
        <td className="px-5 py-3">
          <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-medium", TYPE_COLORS[mem.memory_type] ?? "bg-slate-600 text-slate-200")}>
            {mem.memory_type}
          </span>
        </td>
        <td className="px-5 py-3 font-mono text-xs text-blue-400 max-w-[180px] truncate">{mem.key}</td>
        <td className="px-5 py-3 text-xs text-slate-300 max-w-[240px] truncate">{truncate(mem.value)}</td>
        <td className="px-5 py-3">
          <div className="flex items-center gap-2">
            <div className="w-16 h-1.5 rounded-full bg-slate-700 overflow-hidden">
              <div
                className={cn("h-full rounded-full", relevanceBarColor(mem.relevance_score))}
                style={{ width: `${mem.relevance_score * 100}%` }}
              />
            </div>
            <span className="text-xs text-slate-400">{(mem.relevance_score * 100).toFixed(0)}%</span>
          </div>
        </td>
        <td className="px-5 py-3 text-xs text-slate-400">{mem.access_count}</td>
        <td className="px-5 py-3 text-xs text-slate-400">{timeAgo(mem.created_at)}</td>
      </tr>
      {expanded && (
        <tr className="border-b border-slate-700/50 bg-slate-800/50">
          <td colSpan={7} className="px-5 py-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <Eye className="h-3.5 w-3.5" />
                <span>Full Value</span>
              </div>
              <pre className="rounded-md border border-slate-700 bg-slate-900 p-3 text-xs text-slate-300 overflow-x-auto whitespace-pre-wrap max-h-48">
                {typeof mem.value === "string" ? mem.value : JSON.stringify(mem.value, null, 2)}
              </pre>
              <div className="flex gap-4 text-[10px] text-slate-500">
                <span>ID: {mem.id}</span>
                <span>Agent: {mem.agent_id}</span>
                <span>Last accessed: {mem.last_accessed_at ? timeAgo(mem.last_accessed_at) : "never"}</span>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
