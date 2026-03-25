"use client";

/**
 * TriagePanel — AI-powered triage analysis panel for a security finding.
 *
 * Displays:
 * - Suggested severity with confidence score
 * - AI rationale (natural language explanation)
 * - MITRE ATT&CK tactics identified
 * - Attack path blast radius + choke points
 * - Full audit trail of agent invocations
 *
 * Safety: AI suggestions are clearly labelled as AI-generated.
 *         The authoritative severity is always shown alongside.
 */

import { useState } from "react";
import {
  Brain,
  Network,
  Shield,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Clock,
  Cpu,
  CheckCircle2,
  GitBranch,
  Wrench,
  Bell,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import {
  useTriageResult,
  useAttackPathResult,
  useAgentAuditLogs,
  useRootCauseResult,
  useRemediationPlan,
  triggerTriage,
  triggerAttackPath,
  triggerRootCause,
  triggerRemediationPlan,
  triggerNotification,
} from "@/lib/hooks/use-agents";

// ── Severity color map ────────────────────────────────────────────────────────
const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-800 border border-red-200",
  high: "bg-orange-100 text-orange-800 border border-orange-200",
  medium: "bg-yellow-100 text-yellow-800 border border-yellow-200",
  low: "bg-blue-100 text-blue-800 border border-blue-200",
  info: "bg-slate-100 text-slate-700 border border-slate-200",
};

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 80 ? "bg-green-500" : pct >= 50 ? "bg-yellow-500" : "bg-red-400";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-slate-500 font-mono w-8 text-right">{pct}%</span>
    </div>
  );
}

function ModelBadge({ model }: { model: string }) {
  const isOllama = model.startsWith("ollama/");
  const isClaude = model.startsWith("claude-");
  const isNone = model === "none";

  if (isNone) return <span className="text-xs text-slate-400">— no LLM needed</span>;

  return (
    <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-mono ${
      isClaude ? "bg-purple-50 text-purple-700 border border-purple-200" :
      isOllama ? "bg-green-50 text-green-700 border border-green-200" :
      "bg-slate-100 text-slate-600"
    }`}>
      <Cpu className="h-3 w-3" />
      {model}
    </span>
  );
}

// ── Triage Section ────────────────────────────────────────────────────────────

function TriageSection({ findingId }: { findingId: string }) {
  const { result, isLoading, error, mutate } = useTriageResult(findingId);
  const [running, setRunning] = useState(false);

  async function handleRun() {
    setRunning(true);
    try {
      await triggerTriage(findingId);
      mutate();
      // Auto-chain: trigger root cause + notification silently
      Promise.allSettled([
        triggerRootCause(findingId),
        triggerNotification(findingId),
      ]).catch(() => {});
    } catch (err) {
      console.error(err);
    } finally {
      setRunning(false);
    }
  }

  const notTriaged = !isLoading && (error || !result);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4 text-purple-600" />
          <span className="text-sm font-semibold text-slate-800">AI Triage</span>
          <span className="text-xs text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">THINK agent</span>
        </div>
        <button
          onClick={handleRun}
          disabled={running || isLoading}
          className="inline-flex items-center gap-1.5 text-xs text-purple-600 hover:text-purple-700 disabled:opacity-40 transition-colors"
        >
          {running ? <Spinner className="h-3 w-3" /> : <RefreshCw className="h-3 w-3" />}
          {result ? "Re-triage" : "Run Triage"}
        </button>
      </div>

      {isLoading && (
        <div className="flex justify-center py-4">
          <Spinner className="h-5 w-5 text-purple-400" />
        </div>
      )}

      {notTriaged && !running && (
        <div className="text-center py-6 text-sm text-slate-400 bg-slate-50 rounded-lg border border-dashed border-slate-200">
          <Brain className="h-8 w-8 mx-auto mb-2 text-slate-300" />
          No triage analysis yet. Click "Run Triage" to analyze with AI.
        </div>
      )}

      {result && (
        <div className="space-y-3">
          {/* Suggested severity */}
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1">
              <p className="text-xs text-slate-500 mb-1">AI Suggested Severity</p>
              <div className="flex items-center gap-2">
                <span className={`text-xs font-semibold px-2.5 py-1 rounded-full uppercase ${SEVERITY_COLORS[result.output.suggested_severity] || SEVERITY_COLORS.info}`}>
                  {result.output.suggested_severity}
                </span>
                {result.output.fallback_used && (
                  <span className="text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
                    fallback mode
                  </span>
                )}
              </div>
            </div>
            <div className="flex-1">
              <p className="text-xs text-slate-500 mb-1">Confidence</p>
              <ConfidenceBar value={result.output.confidence} />
            </div>
          </div>

          {/* Rationale */}
          <div className="bg-purple-50/70 rounded-lg p-3 border border-purple-100">
            <p className="text-xs font-medium text-purple-700 mb-1">AI Rationale</p>
            <p className="text-xs text-slate-700 leading-relaxed">{result.output.rationale}</p>
          </div>

          {/* MITRE Tactics */}
          {result.output.mitre_tactics.length > 0 && (
            <div>
              <p className="text-xs text-slate-500 mb-1.5">MITRE ATT&CK Tactics</p>
              <div className="flex flex-wrap gap-1.5">
                {result.output.mitre_tactics.map(tactic => (
                  <span key={tactic} className="text-xs bg-slate-800 text-slate-200 px-2 py-0.5 rounded-full font-mono">
                    {tactic}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Metadata */}
          <div className="flex items-center gap-3 pt-1 border-t border-slate-100">
            <ModelBadge model={result.model_used} />
            {result.latency_ms && (
              <span className="text-xs text-slate-400 flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {(result.latency_ms / 1000).toFixed(1)}s
              </span>
            )}
            <span className="text-xs text-slate-400 ml-auto">
              {new Date(result.created_at).toLocaleDateString()}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Attack Path Section ───────────────────────────────────────────────────────

function AttackPathSection({ findingId }: { findingId: string }) {
  const { result, isLoading, error, mutate } = useAttackPathResult(findingId);
  const [running, setRunning] = useState(false);

  async function handleRun() {
    setRunning(true);
    try {
      await triggerAttackPath(findingId);
      mutate();
    } catch (err) {
      console.error(err);
    } finally {
      setRunning(false);
    }
  }

  const notAnalyzed = !isLoading && (error || !result);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Network className="h-4 w-4 text-blue-600" />
          <span className="text-sm font-semibold text-slate-800">Attack Path</span>
          <span className="text-xs text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">graph BFS</span>
        </div>
        <button
          onClick={handleRun}
          disabled={running || isLoading}
          className="inline-flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-700 disabled:opacity-40 transition-colors"
        >
          {running ? <Spinner className="h-3 w-3" /> : <RefreshCw className="h-3 w-3" />}
          {result ? "Re-analyze" : "Analyze"}
        </button>
      </div>

      {isLoading && (
        <div className="flex justify-center py-4">
          <Spinner className="h-5 w-5 text-blue-400" />
        </div>
      )}

      {notAnalyzed && !running && (
        <div className="text-center py-6 text-sm text-slate-400 bg-slate-50 rounded-lg border border-dashed border-slate-200">
          <Network className="h-8 w-8 mx-auto mb-2 text-slate-300" />
          No attack path analysis yet. Click "Analyze" to run graph traversal.
        </div>
      )}

      {result && (
        <div className="space-y-3">
          {/* Blast radius */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-red-50 rounded-lg p-3 border border-red-100">
              <p className="text-xs text-red-500 mb-1">Blast Radius</p>
              <p className="text-2xl font-bold text-red-700">{result.output.blast_radius_count}</p>
              <p className="text-xs text-red-400">reachable nodes</p>
            </div>
            <div className="bg-amber-50 rounded-lg p-3 border border-amber-100">
              <p className="text-xs text-amber-600 mb-1">Choke Points</p>
              <p className="text-2xl font-bold text-amber-700">{result.output.choke_points.length}</p>
              <p className="text-xs text-amber-500">high-degree nodes</p>
            </div>
          </div>

          {/* Attack chain */}
          {result.output.attack_chain.length > 0 && (
            <div>
              <p className="text-xs text-slate-500 mb-1.5">Attack Chain</p>
              <div className="flex flex-wrap items-center gap-1">
                {result.output.attack_chain.map((node, i) => (
                  <span key={i} className="flex items-center gap-1">
                    <span className="text-xs bg-slate-800 text-white px-2 py-0.5 rounded font-mono">
                      {node}
                    </span>
                    {i < result.output.attack_chain.length - 1 && (
                      <span className="text-slate-400 text-xs">→</span>
                    )}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Choke points list */}
          {result.output.choke_points.length > 0 && (
            <div>
              <p className="text-xs text-slate-500 mb-1.5">Choke Points to Prioritize</p>
              <div className="flex flex-wrap gap-1.5">
                {result.output.choke_points.map(cp => (
                  <span key={cp} className="text-xs bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full border border-amber-200 font-mono">
                    ⚡ {cp}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* NL summary */}
          <div className="bg-blue-50/70 rounded-lg p-3 border border-blue-100">
            <p className="text-xs font-medium text-blue-700 mb-1">AI Path Summary</p>
            <p className="text-xs text-slate-700 leading-relaxed">{result.output.path_summary}</p>
          </div>

          {/* Metadata */}
          <div className="flex items-center gap-3 pt-1 border-t border-slate-100">
            <ModelBadge model={result.model_used} />
            {result.latency_ms && (
              <span className="text-xs text-slate-400 flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {(result.latency_ms / 1000).toFixed(1)}s
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Root Cause Section ────────────────────────────────────────────────────────

const PRIORITY_COLORS: Record<string, string> = {
  immediate: "bg-red-100 text-red-800 border border-red-200",
  high: "bg-orange-100 text-orange-800 border border-orange-200",
  medium: "bg-yellow-100 text-yellow-800 border border-yellow-200",
  low: "bg-blue-100 text-blue-800 border border-blue-200",
};

function RootCauseSection({ findingId }: { findingId: string }) {
  const { result, isLoading, error, mutate } = useRootCauseResult(findingId);
  const [running, setRunning] = useState(false);

  async function handleRun() {
    setRunning(true);
    try {
      await triggerRootCause(findingId);
      mutate();
    } catch (err) {
      console.error(err);
    } finally {
      setRunning(false);
    }
  }

  const notAnalyzed = !isLoading && (error || !result);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GitBranch className="h-4 w-4 text-amber-600" />
          <span className="text-sm font-semibold text-slate-800">Root Cause</span>
          <span className="text-xs text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">THINK agent</span>
        </div>
        <button
          onClick={handleRun}
          disabled={running || isLoading}
          className="inline-flex items-center gap-1.5 text-xs text-amber-600 hover:text-amber-700 disabled:opacity-40 transition-colors"
        >
          {running ? <Spinner className="h-3 w-3" /> : <RefreshCw className="h-3 w-3" />}
          {result ? "Re-analyze" : "Analyze"}
        </button>
      </div>

      {isLoading && <div className="flex justify-center py-4"><Spinner className="h-5 w-5 text-amber-400" /></div>}

      {notAnalyzed && !running && (
        <div className="text-center py-6 text-sm text-slate-400 bg-slate-50 rounded-lg border border-dashed border-slate-200">
          <GitBranch className="h-8 w-8 mx-auto mb-2 text-slate-300" />
          No root cause analysis yet. Run Triage first or click "Analyze".
        </div>
      )}

      {result && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-xs font-semibold px-2.5 py-1 rounded-full uppercase ${PRIORITY_COLORS[result.output.remediation_priority] || PRIORITY_COLORS.medium}`}>
              {result.output.remediation_priority} priority
            </span>
            <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded border">
              {result.output.misconfiguration_type}
            </span>
            {result.output.affected_blast_radius > 0 && (
              <span className="text-xs bg-red-50 text-red-700 px-2 py-0.5 rounded border border-red-200">
                ~{result.output.affected_blast_radius} at risk
              </span>
            )}
          </div>

          <div className="bg-amber-50/70 rounded-lg p-3 border border-amber-100">
            <p className="text-xs font-medium text-amber-700 mb-1">Root Cause</p>
            <p className="text-xs text-slate-700 leading-relaxed">{result.output.root_cause}</p>
          </div>

          {result.output.contributing_factors.length > 0 && (
            <div>
              <p className="text-xs text-slate-500 mb-1.5">Contributing Factors</p>
              <ul className="space-y-1">
                {result.output.contributing_factors.map((f, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-xs text-slate-600">
                    <span className="text-amber-500 mt-0.5">•</span>
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex items-center gap-3 pt-1 border-t border-slate-100">
            <ModelBadge model={result.model_used} />
            {result.latency_ms && (
              <span className="text-xs text-slate-400 flex items-center gap-1">
                <Clock className="h-3 w-3" />{(result.latency_ms / 1000).toFixed(1)}s
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Remediation Plan Section ──────────────────────────────────────────────────

const IAC_COLORS: Record<string, string> = {
  terraform: "bg-green-100 text-green-800 border border-green-200",
  cli: "bg-blue-100 text-blue-800 border border-blue-200",
  console: "bg-slate-100 text-slate-600 border border-slate-200",
};

function RemediationSection({ findingId }: { findingId: string }) {
  const { result, isLoading, error, mutate } = useRemediationPlan(findingId);
  const [running, setRunning] = useState(false);

  async function handleRun() {
    setRunning(true);
    try {
      await triggerRemediationPlan(findingId);
      mutate();
    } catch (err) {
      console.error(err);
    } finally {
      setRunning(false);
    }
  }

  const notPlanned = !isLoading && (error || !result);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Wrench className="h-4 w-4 text-green-600" />
          <span className="text-sm font-semibold text-slate-800">Remediation Plan</span>
          <span className="text-xs text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">THINK agent</span>
        </div>
        <button
          onClick={handleRun}
          disabled={running || isLoading}
          className="inline-flex items-center gap-1.5 text-xs text-green-600 hover:text-green-700 disabled:opacity-40 transition-colors"
        >
          {running ? <Spinner className="h-3 w-3" /> : <RefreshCw className="h-3 w-3" />}
          {result ? "Re-plan" : "Generate Plan"}
        </button>
      </div>

      {isLoading && <div className="flex justify-center py-4"><Spinner className="h-5 w-5 text-green-400" /></div>}

      {notPlanned && !running && (
        <div className="text-center py-6 text-sm text-slate-400 bg-slate-50 rounded-lg border border-dashed border-slate-200">
          <Wrench className="h-8 w-8 mx-auto mb-2 text-slate-300" />
          No remediation plan yet. Click "Generate Plan" to create IaC steps.
        </div>
      )}

      {result && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded border">
              ⏱ {result.output.estimated_effort}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded border font-medium ${result.output.auto_remediatable ? "bg-green-50 text-green-700 border-green-200" : "bg-slate-50 text-slate-600 border-slate-200"}`}>
              {result.output.auto_remediatable ? "✓ Auto-remediatable" : "Manual required"}
            </span>
          </div>

          <div className="space-y-2">
            {result.output.steps.map((step) => (
              <div key={step.step} className="rounded-lg border border-slate-200 overflow-hidden">
                <div className="flex items-center gap-2 px-3 py-2 bg-slate-50">
                  <span className="text-xs font-bold text-slate-500 w-5 text-center">{step.step}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded font-mono uppercase ${IAC_COLORS[step.iac_type] || IAC_COLORS.console}`}>
                    {step.iac_type}
                  </span>
                  <span className="text-xs font-medium text-slate-800">{step.action}</span>
                </div>
                <pre className="text-xs font-mono bg-slate-900 text-green-400 px-3 py-2 overflow-x-auto whitespace-pre-wrap leading-relaxed">
                  {step.command}
                </pre>
              </div>
            ))}
          </div>

          <div className="flex items-center gap-3 pt-1 border-t border-slate-100">
            <ModelBadge model={result.model_used} />
            {result.latency_ms && (
              <span className="text-xs text-slate-400 flex items-center gap-1">
                <Clock className="h-3 w-3" />{(result.latency_ms / 1000).toFixed(1)}s
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Audit Log Section ─────────────────────────────────────────────────────────

function AuditLogSection({ findingId }: { findingId: string }) {
  const { logs, isLoading } = useAgentAuditLogs(findingId);
  const [expanded, setExpanded] = useState(false);

  if (isLoading) return null;
  if (logs.length === 0) return null;

  const displayLogs = expanded ? logs : logs.slice(0, 3);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="h-4 w-4 text-slate-500" />
          <span className="text-sm font-semibold text-slate-700">Agent Audit Trail</span>
          <span className="text-xs bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded-full">{logs.length}</span>
        </div>
        {logs.length > 3 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-slate-500 hover:text-slate-700 flex items-center gap-1"
          >
            {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            {expanded ? "Show less" : `+${logs.length - 3} more`}
          </button>
        )}
      </div>

      <div className="space-y-1.5">
        {displayLogs.map(log => (
          <div key={log.id} className="flex items-start gap-2.5 text-xs text-slate-600 bg-slate-50 rounded-lg px-3 py-2 border border-slate-100">
            <CheckCircle2 className="h-3.5 w-3.5 text-green-500 mt-0.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-slate-800">{log.agent_name}</span>
                <span className="text-slate-400">·</span>
                <ModelBadge model={log.model_used} />
                {log.latency_ms && (
                  <span className="text-slate-400 ml-auto">{(log.latency_ms / 1000).toFixed(1)}s</span>
                )}
              </div>
              {log.output_summary && (
                <p className="text-slate-500 truncate mt-0.5">{log.output_summary.slice(0, 100)}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main TriagePanel component ────────────────────────────────────────────────

interface TriagePanelProps {
  findingId: string;
}

export function TriagePanel({ findingId }: TriagePanelProps) {
  const [activeTab, setActiveTab] = useState<"triage" | "attack_path" | "root_cause" | "remediation" | "audit">("triage");

  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 bg-gradient-to-r from-purple-50 to-blue-50 border-b border-slate-200">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-white rounded-lg shadow-sm">
            <Brain className="h-4 w-4 text-purple-600" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900">AI Analysis</h3>
            <p className="text-xs text-slate-500">Powered by THINK agents (Ollama llama3 + Claude Haiku)</p>
          </div>
          <div className="ml-auto">
            <span className="text-xs bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 rounded-full font-medium">
              AI-generated · not authoritative
            </span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200">
        {[
          { id: "triage" as const, label: "Triage", icon: Brain },
          { id: "attack_path" as const, label: "Attack Path", icon: Network },
          { id: "root_cause" as const, label: "Root Cause", icon: GitBranch },
          { id: "remediation" as const, label: "Remediation", icon: Wrench },
          { id: "audit" as const, label: "Audit Trail", icon: Shield },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium transition-colors ${
              activeTab === id
                ? "text-purple-700 border-b-2 border-purple-600 bg-purple-50/50"
                : "text-slate-500 hover:text-slate-700 hover:bg-slate-50"
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="p-4">
        {activeTab === "triage" && <TriageSection findingId={findingId} />}
        {activeTab === "attack_path" && <AttackPathSection findingId={findingId} />}
        {activeTab === "root_cause" && <RootCauseSection findingId={findingId} />}
        {activeTab === "remediation" && <RemediationSection findingId={findingId} />}
        {activeTab === "audit" && <AuditLogSection findingId={findingId} />}
      </div>
    </div>
  );
}
