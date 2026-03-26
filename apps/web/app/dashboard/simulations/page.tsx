"use client";

import { useState, useRef, useEffect } from "react";
import {
  Zap, Play, Users, MessageSquare, Shield, Trophy, Clock, DollarSign,
  ChevronDown, ChevronRight, AlertTriangle, CheckCircle2, XCircle, Loader2,
} from "lucide-react";
import {
  useSimulations,
  useSimulationDetail,
  launchSimulation,
  deleteSimulation,
  type SimulationRun,
  type SwarmAgent,
  type CommMessage,
  type ValidationGate,
} from "@/lib/hooks/use-simulations";
import { Spinner } from "@/components/ui/spinner";
import { TimelineTab } from "@/components/simulation/timeline-tab";
import { AgentSolutionTabs } from "@/components/simulation/agent-solution-tabs";
import { FullscreenSolutionModal } from "@/components/simulation/fullscreen-solution-modal";
import { ActionLoopSvg } from "@/components/simulation/action-loop-svg";
import { StatusIndicator } from "@/components/ui/status-indicator";

// ── Status mapping for StatusIndicator ───────────────────────────────────────
const STATUS_TO_INDICATOR: Record<string, "standby" | "running" | "certified" | "error"> = {
  pending:   "standby",
  running:   "running",
  completed: "certified",
  failed:    "error",
};

// ── Constants ────────────────────────────────────────────────────────────────

const WIZ_CNAPP_DOMAINS = [
  "CSPM", "DSPM", "KSPP", "Vuln-Mgmt", "IaC-Scan",
  "CI-CD-Scan", "CDR", "CIEM", "ASPM", "AICURITY",
] as const;

const GAP_DOMAINS = [
  "Data-Lineage", "AI-BOM", "Runtime-Sensor",
  "Custom-Policy-DSL", "Multi-Cloud-Parity",
  "Compliance-Attestation", "Cost-Attribution",
] as const;

const STATUS_COLORS: Record<string, string> = {
  pending:   "bg-slate-600 text-slate-200",
  running:   "bg-blue-600 text-blue-100",
  completed: "bg-emerald-600 text-emerald-100",
  failed:    "bg-red-600 text-red-100",
};

const AGENT_STATUS_COLORS: Record<string, string> = {
  idle:     "bg-slate-600 text-slate-200",
  running:  "bg-blue-600 text-blue-100",
  done:     "bg-emerald-600 text-emerald-100",
  error:    "bg-red-600 text-red-100",
  spawning: "bg-purple-600 text-purple-100",
};

const MSG_TYPE_COLORS: Record<string, string> = {
  info:     "bg-blue-600/20 text-blue-400 border-blue-500/30",
  solution: "bg-emerald-600/20 text-emerald-400 border-emerald-500/30",
  alert:    "bg-red-600/20 text-red-400 border-red-500/30",
  spawn:    "bg-purple-600/20 text-purple-400 border-purple-500/30",
  wiz:      "bg-orange-600/20 text-orange-400 border-orange-500/30",
};

const GATE_STATE_COLORS: Record<string, string> = {
  pass:    "bg-emerald-600 text-emerald-100",
  fail:    "bg-red-600 text-red-100",
  partial: "bg-yellow-600 text-yellow-100",
  pending: "bg-slate-600 text-slate-300",
  running: "bg-blue-600 text-blue-100",
};

// ── Helpers ──────────────────────────────────────────────────────────────────

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(" ");
}

function fmtDuration(seconds: number | null) {
  if (seconds == null) return "--";
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const m = Math.floor(seconds / 60);
  const s = (seconds % 60).toFixed(0);
  return `${m}m ${s}s`;
}

function fmtCost(usd: number) {
  return `$${usd.toFixed(4)}`;
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString();
}

function confidenceColor(score: number) {
  if (score >= 80) return "text-emerald-400";
  if (score >= 60) return "text-yellow-400";
  if (score >= 40) return "text-orange-400";
  return "text-red-400";
}

function confidenceRingColor(score: number) {
  if (score >= 80) return "stroke-emerald-500";
  if (score >= 60) return "stroke-yellow-500";
  if (score >= 40) return "stroke-orange-500";
  return "stroke-red-500";
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function SimulationsPage() {
  const { simulations, isLoading, mutate } = useSimulations();
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [showLaunchPanel, setShowLaunchPanel] = useState(false);
  const [selectedDomain, setSelectedDomain] = useState<string>("");
  const [launching, setLaunching] = useState(false);
  const [fullscreenContent, setFullscreenContent] = useState<string | null>(null);

  const { detail } = useSimulationDetail(selectedRunId);

  // ── Launch handler ───────────────────────────────────────────────────────
  async function handleLaunch() {
    if (!selectedDomain) return;
    setLaunching(true);
    try {
      const run = await launchSimulation(selectedDomain);
      await mutate();
      setSelectedRunId(run.id);
      setShowLaunchPanel(false);
      setSelectedDomain("");
    } catch (err) {
      console.error("Launch failed:", err);
    } finally {
      setLaunching(false);
    }
  }

  // ── Delete handler ───────────────────────────────────────────────────────
  async function handleDelete(runId: string) {
    try {
      await deleteSimulation(runId);
      if (selectedRunId === runId) setSelectedRunId(null);
      await mutate();
    } catch (err) {
      console.error("Delete failed:", err);
    }
  }

  // ── Loading state ────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-slate-900">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <header className="flex items-center justify-between px-6 py-5 border-b border-slate-700">
        <div className="flex items-center gap-3">
          <Zap className="h-6 w-6 text-blue-400" />
          <h1 className="text-xl font-bold tracking-tight">
            OmniSec Simulation Engine
          </h1>
        </div>
        <button
          onClick={() => setShowLaunchPanel((p) => !p)}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 transition-colors"
        >
          <Play className="h-4 w-4" />
          Launch Simulation
        </button>
      </header>

      {/* ── Launch panel ────────────────────────────────────────────────── */}
      {showLaunchPanel && (
        <div className="mx-6 mt-4 rounded-lg border border-slate-700 bg-slate-800 p-5">
          <h2 className="text-sm font-semibold text-slate-300 mb-3">
            Select Domain
          </h2>
          <select
            value={selectedDomain}
            onChange={(e) => setSelectedDomain(e.target.value)}
            className="w-full rounded-md border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none mb-2"
          >
            <option value="">-- choose domain --</option>
            <optgroup label="Wiz CNAPP">
              {WIZ_CNAPP_DOMAINS.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </optgroup>
            <optgroup label="Gap Domains">
              {GAP_DOMAINS.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </optgroup>
          </select>
          <button
            onClick={handleLaunch}
            disabled={!selectedDomain || launching}
            className={cn(
              "mt-3 flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors",
              selectedDomain && !launching
                ? "bg-emerald-600 text-white hover:bg-emerald-500"
                : "bg-slate-700 text-slate-400 cursor-not-allowed"
            )}
          >
            {launching ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Zap className="h-4 w-4" />
            )}
            Run Autopsy
          </button>
        </div>
      )}

      <div className="p-6 space-y-6">
        {/* ── Active simulation detail ──────────────────────────────────── */}
        {detail && (
          <SimulationDetailView
            detail={detail}
            onFullscreen={setFullscreenContent}
          />
        )}

        {/* ── History table ─────────────────────────────────────────────── */}
        <HistoryTable
          simulations={simulations}
          selectedRunId={selectedRunId}
          onSelect={setSelectedRunId}
          onDelete={handleDelete}
        />
      </div>

      {/* ── Fullscreen solution modal ──────────────────────────────────── */}
      {fullscreenContent && (
        <FullscreenSolutionModal
          content={fullscreenContent}
          onClose={() => setFullscreenContent(null)}
        />
      )}
    </div>
  );
}

// ── Simulation detail view ──────────────────────────────────────────────────

function SimulationDetailView({
  detail,
  onFullscreen,
}: {
  detail: NonNullable<ReturnType<typeof useSimulationDetail>["detail"]>;
  onFullscreen: (content: string) => void;
}) {
  const [centerTab, setCenterTab] = useState<"overview" | "timeline" | "solutions">("overview");

  const reportAgent = detail.agents.find(
    (a) => a.agent_id === "REPORT-01" && a.output
  );

  // Determine active agent phase for ActionLoopSvg
  const activeAgent = detail.agents.find((a) => a.status === "running");
  const activePhase = activeAgent
    ? (activeAgent.status === "running" ? "act" : "idle")
    : detail.status === "running"
    ? "observe"
    : "idle";

  return (
    <div className="space-y-5">
      {/* Top bar */}
      <div className="flex flex-wrap items-center gap-4 rounded-lg border border-slate-700 bg-slate-800 px-5 py-4">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-blue-400" />
          <span className="text-lg font-semibold">{detail.domain}</span>
        </div>

        {/* StatusIndicator */}
        <StatusIndicator status={STATUS_TO_INDICATOR[detail.status] ?? "standby"} />

        <span
          className={cn(
            "rounded-full px-3 py-0.5 text-xs font-medium",
            STATUS_COLORS[detail.status]
          )}
        >
          {detail.status}
        </span>

        {/* Action loop miniature */}
        <ActionLoopSvg activePhase={activePhase} size={80} />

        {/* Confidence gauge */}
        <div className="flex items-center gap-2 ml-auto">
          <ConfidenceGauge score={detail.confidence_score} />
        </div>

        <div className="flex items-center gap-4 text-sm text-slate-400">
          <span className="flex items-center gap-1">
            <Clock className="h-4 w-4" />
            {fmtDuration(detail.duration_seconds)}
          </span>
          <span className="flex items-center gap-1">
            <DollarSign className="h-4 w-4" />
            {fmtCost(detail.total_cost_usd)}
          </span>
        </div>
      </div>

      {/* ── Center-panel tab bar ─────────────────────────────────────── */}
      <div className="flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800 p-1">
        {(
          [
            { key: "overview",  label: "Overview" },
            { key: "timeline",  label: "Timeline" },
            { key: "solutions", label: "Solutions" },
          ] as const
        ).map((tab) => (
          <button
            key={tab.key}
            onClick={() => setCenterTab(tab.key)}
            className={cn(
              "flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors",
              centerTab === tab.key
                ? "bg-slate-700 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/50"
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── Tab content ──────────────────────────────────────────────── */}

      {centerTab === "overview" && (
        <>
          {/* Two-column: agents + comms */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Agent roster */}
            <div className="rounded-lg border border-slate-700 bg-slate-800 p-4">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-300 mb-3">
                <Users className="h-4 w-4" />
                Agent Roster ({detail.agents.length})
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {detail.agents.map((agent) => (
                  <AgentCard key={agent.id} agent={agent} />
                ))}
              </div>
            </div>

            {/* Comm bus */}
            <div className="rounded-lg border border-slate-700 bg-slate-800 p-4">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-300 mb-3">
                <MessageSquare className="h-4 w-4" />
                Comm Bus ({detail.messages.length})
              </h3>
              <CommBus messages={detail.messages} />
            </div>
          </div>

          {/* Validation board */}
          <div className="rounded-lg border border-slate-700 bg-slate-800 p-4">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-300 mb-3">
              <Trophy className="h-4 w-4" />
              Validation Board ({detail.gates.length} gates)
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {detail.gates.map((gate) => (
                <GateCard key={gate.gate_number} gate={gate} />
              ))}
            </div>
          </div>

          {/* Solution panel */}
          {reportAgent?.output && (
            <div className="rounded-lg border border-slate-700 bg-slate-800 p-5">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-300 mb-3">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                Solution Report
              </h3>
              <div className="prose prose-invert prose-sm max-w-none text-slate-300 whitespace-pre-wrap">
                {reportAgent.output}
              </div>
            </div>
          )}
        </>
      )}

      {centerTab === "timeline" && (
        <TimelineTab messages={detail.messages} />
      )}

      {centerTab === "solutions" && (
        <AgentSolutionTabs
          agents={detail.agents}
          onFullscreen={(content) => onFullscreen(content)}
        />
      )}

      {/* Error message (always visible regardless of tab) */}
      {detail.error_message && (
        <div className="flex items-start gap-3 rounded-lg border border-red-800 bg-red-900/30 p-4">
          <AlertTriangle className="h-5 w-5 text-red-400 shrink-0 mt-0.5" />
          <p className="text-sm text-red-300">{detail.error_message}</p>
        </div>
      )}
    </div>
  );
}

// ── Confidence gauge ────────────────────────────────────────────────────────

function ConfidenceGauge({ score }: { score: number }) {
  const radius = 20;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="flex items-center gap-2">
      <svg width="52" height="52" className="-rotate-90">
        <circle
          cx="26"
          cy="26"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="4"
          className="text-slate-700"
        />
        <circle
          cx="26"
          cy="26"
          r={radius}
          fill="none"
          strokeWidth="4"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className={confidenceRingColor(score)}
        />
      </svg>
      <div className="text-center">
        <span className={cn("text-lg font-bold", confidenceColor(score))}>
          {score}%
        </span>
        <p className="text-[10px] text-slate-500">confidence</p>
      </div>
    </div>
  );
}

// ── Agent card ──────────────────────────────────────────────────────────────

function AgentCard({ agent }: { agent: SwarmAgent }) {
  return (
    <div className="rounded-md border border-slate-700 bg-slate-900 p-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono font-semibold text-blue-400">
          {agent.agent_id}
        </span>
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-[10px] font-medium",
            AGENT_STATUS_COLORS[agent.status]
          )}
        >
          {agent.status}
        </span>
      </div>
      <p className="text-sm font-medium text-white truncate">{agent.name}</p>
      <p className="text-xs text-slate-500 truncate">{agent.role}</p>

      {/* Progress bar */}
      <div className="w-full h-1.5 rounded-full bg-slate-700 overflow-hidden">
        <div
          className="h-full bg-blue-500 rounded-full transition-all duration-300"
          style={{ width: `${agent.progress}%` }}
        />
      </div>

      {/* Autonomy stars */}
      <div className="flex items-center justify-between text-[10px] text-slate-500">
        <span>
          Autonomy{" "}
          {"★".repeat(agent.autonomy_level)}
          {"☆".repeat(Math.max(0, 5 - agent.autonomy_level))}
        </span>
        {agent.spawn_authority && (
          <span className="text-purple-400">spawn</span>
        )}
      </div>
    </div>
  );
}

// ── Comm bus ─────────────────────────────────────────────────────────────────

function CommBus({ messages }: { messages: CommMessage[] }) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages.length]);

  if (messages.length === 0) {
    return (
      <p className="text-xs text-slate-500 text-center py-6">
        No messages yet.
      </p>
    );
  }

  return (
    <div
      ref={scrollRef}
      className="max-h-80 overflow-y-auto space-y-2 pr-1 scrollbar-thin scrollbar-thumb-slate-700"
    >
      {messages.map((msg) => (
        <div
          key={msg.id}
          className="rounded-md border border-slate-700 bg-slate-900 p-2.5 text-xs space-y-1"
        >
          <div className="flex items-center gap-2">
            <span className="font-mono text-blue-400">
              {msg.from_agent_id}
            </span>
            <ChevronRight className="h-3 w-3 text-slate-600" />
            <span className="font-mono text-blue-400">{msg.to_agent_id}</span>
            <span
              className={cn(
                "ml-auto rounded-full border px-2 py-0.5 text-[10px] font-medium",
                MSG_TYPE_COLORS[msg.message_type]
              )}
            >
              {msg.message_type}
            </span>
          </div>
          <p className="text-slate-300 leading-relaxed">{msg.body}</p>
          <p className="text-[10px] text-slate-600">
            {fmtDate(msg.created_at)}
          </p>
        </div>
      ))}
    </div>
  );
}

// ── Gate card ────────────────────────────────────────────────────────────────

function GateCard({ gate }: { gate: ValidationGate }) {
  const stateIcon = () => {
    switch (gate.state) {
      case "pass":
        return <CheckCircle2 className="h-4 w-4 text-emerald-400" />;
      case "fail":
        return <XCircle className="h-4 w-4 text-red-400" />;
      case "running":
        return <Loader2 className="h-4 w-4 text-blue-400 animate-spin" />;
      case "partial":
        return <AlertTriangle className="h-4 w-4 text-yellow-400" />;
      default:
        return <Clock className="h-4 w-4 text-slate-500" />;
    }
  };

  return (
    <div className="rounded-md border border-slate-700 bg-slate-900 p-3 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {stateIcon()}
          <span className="text-xs font-semibold text-white">
            G{gate.gate_number}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {gate.is_double_weight && (
            <Zap className="h-3 w-3 text-yellow-400" title="Double weight" />
          )}
          <span
            className={cn(
              "rounded-full px-2 py-0.5 text-[10px] font-medium",
              GATE_STATE_COLORS[gate.state]
            )}
          >
            {gate.state}
          </span>
        </div>
      </div>
      <p className="text-sm text-slate-300 leading-snug">{gate.name}</p>

      {/* Score bar */}
      <div className="w-full h-1.5 rounded-full bg-slate-700 overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-300",
            gate.state === "pass"
              ? "bg-emerald-500"
              : gate.state === "fail"
              ? "bg-red-500"
              : gate.state === "partial"
              ? "bg-yellow-500"
              : "bg-slate-600"
          )}
          style={{ width: `${gate.score}%` }}
        />
      </div>

      <div className="flex items-center justify-between text-[10px] text-slate-500">
        <span>{gate.score}%</span>
        <span
          className={cn(
            "rounded-full border px-1.5 py-0.5",
            gate.coverage === "wiz"
              ? "border-orange-500/40 text-orange-400"
              : gate.coverage === "swarm"
              ? "border-blue-500/40 text-blue-400"
              : "border-emerald-500/40 text-emerald-400"
          )}
        >
          {gate.coverage}
        </span>
      </div>
    </div>
  );
}

// ── History table ───────────────────────────────────────────────────────────

function HistoryTable({
  simulations,
  selectedRunId,
  onSelect,
  onDelete,
}: {
  simulations: SimulationRun[];
  selectedRunId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  if (simulations.length === 0) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-800 p-8 text-center">
        <Zap className="h-8 w-8 text-slate-600 mx-auto mb-3" />
        <p className="text-sm text-slate-400">
          No simulation runs yet. Launch one to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 overflow-hidden">
      <div className="px-5 py-3 border-b border-slate-700">
        <h3 className="text-sm font-semibold text-slate-300">
          Simulation History
        </h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 text-left text-xs text-slate-500">
              <th className="px-5 py-2.5 font-medium">Domain</th>
              <th className="px-5 py-2.5 font-medium">Status</th>
              <th className="px-5 py-2.5 font-medium">Confidence</th>
              <th className="px-5 py-2.5 font-medium">Duration</th>
              <th className="px-5 py-2.5 font-medium">Cost</th>
              <th className="px-5 py-2.5 font-medium">Date</th>
              <th className="px-5 py-2.5 font-medium" />
            </tr>
          </thead>
          <tbody>
            {simulations.map((run) => (
              <tr
                key={run.id}
                onClick={() => onSelect(run.id)}
                className={cn(
                  "border-b border-slate-700/50 cursor-pointer transition-colors",
                  selectedRunId === run.id
                    ? "bg-blue-600/10"
                    : "hover:bg-slate-700/30"
                )}
              >
                <td className="px-5 py-3 font-medium text-white">
                  {run.domain}
                </td>
                <td className="px-5 py-3">
                  <span
                    className={cn(
                      "rounded-full px-2.5 py-0.5 text-xs font-medium",
                      STATUS_COLORS[run.status]
                    )}
                  >
                    {run.status}
                  </span>
                </td>
                <td className="px-5 py-3">
                  <span className={confidenceColor(run.confidence_score)}>
                    {run.confidence_score}%
                  </span>
                </td>
                <td className="px-5 py-3 text-slate-400">
                  {fmtDuration(run.duration_seconds)}
                </td>
                <td className="px-5 py-3 text-slate-400">
                  {fmtCost(run.total_cost_usd)}
                </td>
                <td className="px-5 py-3 text-slate-400">
                  {fmtDate(run.created_at)}
                </td>
                <td className="px-5 py-3">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(run.id);
                    }}
                    className="text-xs text-slate-500 hover:text-red-400 transition-colors"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
