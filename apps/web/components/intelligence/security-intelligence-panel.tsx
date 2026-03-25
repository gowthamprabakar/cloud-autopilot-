"use client";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { useFindingIntelligence } from "@/lib/hooks/use-intelligence";
import { RAGBadge, RAGIndicatorBar } from "./rag-badge";
import { Spinner } from "@/components/ui/spinner";
import { apiClient } from "@/lib/api-client";
import type { FindingIntelligence, PrioritizedAction, CausalFactor, ToxicCombo } from "@/lib/types";

// ── Helpers ──────────────────────────────────────────────────────────────────

function rootCauseLabel(cause: string): string {
  const map: Record<string, string> = {
    network_misconfiguration: "Network Misconfiguration",
    iam_misconfiguration:     "IAM Misconfiguration",
    governance_gap:           "Governance Gap",
    config_drift:             "Configuration Drift",
    access_control_failure:   "Access Control Failure",
    missing_guardrail:        "Missing Guardrail",
  };
  return map[cause] ?? cause.replace(/_/g, " ");
}

function rootCauseIcon(cause: string): string {
  const map: Record<string, string> = {
    network_misconfiguration: "🌐",
    iam_misconfiguration:     "🔑",
    governance_gap:           "🏛️",
    config_drift:             "⚙️",
    access_control_failure:   "🚪",
    missing_guardrail:        "🛡️",
  };
  return map[cause] ?? "⚠️";
}

function effortColor(effort: PrioritizedAction["effort"]): string {
  return effort === "LOW" ? "bg-green-100 text-green-700" : effort === "MEDIUM" ? "bg-amber-100 text-amber-700" : "bg-red-100 text-red-700";
}

function impactColor(impact: PrioritizedAction["impact"]): string {
  if (impact === "CRITICAL") return "bg-red-600 text-white";
  if (impact === "HIGH")     return "bg-orange-100 text-orange-700";
  if (impact === "MEDIUM")   return "bg-amber-100 text-amber-700";
  return "bg-green-100 text-green-700";
}

function scoreColor(score: number): string {
  if (score >= 75) return "bg-red-500";
  if (score >= 50) return "bg-amber-500";
  return "bg-green-500";
}

// ── Sub-components ────────────────────────────────────────────────────────────

function InfoBox({ children, color }: { children: React.ReactNode; color: "blue" | "green" | "yellow" | "red" }) {
  const map = {
    blue:   "bg-blue-50 border-blue-200 text-blue-900",
    green:  "bg-green-50 border-green-200 text-green-900",
    yellow: "bg-yellow-50 border-yellow-200 text-yellow-900",
    red:    "bg-red-50 border-red-200 text-red-900",
  };
  return (
    <div className={cn("rounded-lg border p-4 text-sm leading-relaxed", map[color])}>
      {children}
    </div>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <button
      onClick={copy}
      className="ml-2 shrink-0 rounded px-2 py-0.5 text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors"
    >
      {copied ? "Copied!" : "Copy"}
    </button>
  );
}

function ActionCard({ action, index }: { action: PrioritizedAction; index: number }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <span className="text-sm font-semibold text-slate-900">{index + 1}. {action.title}</span>
        <div className="flex gap-1.5 shrink-0">
          <span className={cn("px-1.5 py-0.5 rounded text-xs font-medium", effortColor(action.effort))}>
            {action.effort}
          </span>
          <span className={cn("px-1.5 py-0.5 rounded text-xs font-medium", impactColor(action.impact))}>
            {action.impact}
          </span>
        </div>
      </div>
      <p className="text-xs text-slate-600 leading-relaxed">{action.description}</p>
      {action.cli_command && (
        <div className="flex items-center rounded bg-slate-900 px-3 py-2 text-xs font-mono text-green-400 overflow-x-auto">
          <code className="flex-1 whitespace-pre">{action.cli_command}</code>
          <CopyButton text={action.cli_command} />
        </div>
      )}
      {action.console_url && (
        <a
          href={action.console_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
        >
          Open in AWS Console →
        </a>
      )}
    </div>
  );
}

function CausalFactorBar({ factor }: { factor: CausalFactor }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-slate-700 capitalize">{factor.name.replace(/_/g, " ")}</span>
        <span className="text-xs text-slate-500">{Math.round(factor.score * 100)}%</span>
      </div>
      <div className="h-2 rounded-full bg-slate-100">
        <div
          className={cn("h-2 rounded-full transition-all", scoreColor(factor.score * 100))}
          style={{ width: `${Math.min(100, factor.score * 100)}%` }}
        />
      </div>
      {factor.evidence.length > 0 && (
        <ul className="mt-1 space-y-0.5">
          {factor.evidence.slice(0, 3).map((ev, i) => (
            <li key={i} className="text-xs text-slate-500 pl-2 border-l-2 border-slate-200">{ev}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ── Tabs ─────────────────────────────────────────────────────────────────────

type Tab = "overview" | "rootcause" | "recommendations" | "impact";
const TABS: { id: Tab; label: string }[] = [
  { id: "overview",        label: "Overview" },
  { id: "rootcause",       label: "Root Cause" },
  { id: "recommendations", label: "Recommendations" },
  { id: "impact",          label: "Impact" },
];

// ── Tab Panels ────────────────────────────────────────────────────────────────

function OverviewTab({ intel }: { intel: FindingIntelligence }) {
  return (
    <div className="space-y-4">
      {intel.fallback_used && (
        <p className="text-xs italic text-slate-500">AI analysis unavailable — showing template analysis</p>
      )}
      {intel.what_is_it && (
        <div>
          <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">What Is It?</h4>
          <InfoBox color="blue">{intel.what_is_it}</InfoBox>
        </div>
      )}
      {intel.current_state && (
        <div>
          <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Current State</h4>
          <p className="text-sm text-slate-700 leading-relaxed">{intel.current_state}</p>
        </div>
      )}
      {intel.expected_state && (
        <div>
          <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Expected State</h4>
          <InfoBox color="green">{intel.expected_state}</InfoBox>
        </div>
      )}
      {intel.business_impact && (
        <div>
          <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Business Impact</h4>
          <InfoBox color="yellow">{intel.business_impact}</InfoBox>
        </div>
      )}
      {intel.attack_scenario && (
        <div>
          <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">⚠️ Attack Scenario</h4>
          <InfoBox color="red">{intel.attack_scenario}</InfoBox>
        </div>
      )}
    </div>
  );
}

function RootCauseTab({ intel }: { intel: FindingIntelligence }) {
  const score = intel.rag_composite_score ?? intel.composite_score ?? 0;
  const confidence = intel.confidence ?? 0;

  return (
    <div className="space-y-5">
      {intel.rag_level && <RAGIndicatorBar activeLevel={intel.rag_level} />}

      {/* Composite score */}
      <div className="space-y-1">
        <div className="flex justify-between items-center">
          <span className="text-sm font-medium text-slate-700">Composite Risk Score</span>
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-slate-900">{score.toFixed(1)}</span>
            <span className={cn("px-1.5 py-0.5 rounded text-xs font-medium",
              confidence >= 0.8 ? "bg-green-100 text-green-700" :
              confidence >= 0.5 ? "bg-amber-100 text-amber-700" : "bg-red-100 text-red-700"
            )}>
              {Math.round(confidence * 100)}% confidence
            </span>
          </div>
        </div>
        <div className="h-3 rounded-full bg-slate-100">
          <div
            className={cn("h-3 rounded-full transition-all", scoreColor(score))}
            style={{ width: `${Math.min(100, score)}%` }}
          />
        </div>
      </div>

      {/* Primary root cause */}
      {intel.primary_root_cause && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Primary Root Cause</p>
          <p className="text-xl font-bold text-slate-900">
            {rootCauseIcon(intel.primary_root_cause)} {rootCauseLabel(intel.primary_root_cause)}
          </p>
        </div>
      )}

      {/* Causal chain */}
      {intel.causal_chain.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Causal Chain</p>
          <div className="flex flex-wrap items-center gap-1">
            {intel.causal_chain.map((step, i) => (
              <div key={i} className="flex items-center gap-1">
                <span className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-700 capitalize">{step.replace(/_/g, " ")}</span>
                {i < intel.causal_chain.length - 1 && <span className="text-slate-400">→</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Contributing factors */}
      {intel.causal_factors.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Contributing Factors</p>
          <div className="space-y-4">
            {intel.causal_factors.map((factor, i) => (
              <CausalFactorBar key={i} factor={factor} />
            ))}
          </div>
        </div>
      )}

      {/* Toxic combinations */}
      {intel.toxic_combinations.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Toxic Combinations</p>
          <div className="space-y-2">
            {intel.toxic_combinations.map((combo, i) => (
              <ToxicComboCard key={i} combo={combo} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ToxicComboCard({ combo }: { combo: ToxicCombo }) {
  // Support both new (factors_involved / score_boost) and legacy (tags / severity_boost) shapes
  const tags = combo.factors_involved ?? combo.tags ?? [];
  const boost = combo.score_boost ?? combo.severity_boost ?? 0;
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-3">
      {combo.name && (
        <p className="text-xs font-semibold text-red-700 mb-1.5">{combo.name.replace(/_/g, " ").replace(/\+/g, " + ")}</p>
      )}
      <div className="flex flex-wrap gap-1 mb-1.5">
        {tags.map((tag, i) => (
          <span key={i} className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
            {tag.replace(/_/g, " ")}
          </span>
        ))}
        <span className="ml-auto text-xs font-bold text-red-600">+{(boost * 100).toFixed(0)}% risk</span>
      </div>
      <p className="text-xs text-red-800 leading-relaxed">{combo.description}</p>
    </div>
  );
}

function RecommendationsTab({ intel }: { intel: FindingIntelligence }) {
  const sla = intel.sla_days;
  const slaColor = sla !== null ? (sla <= 1 ? "text-red-600" : sla <= 7 ? "text-amber-600" : "text-green-600") : "text-slate-500";

  return (
    <div className="space-y-6">
      {/* SLA + escalation */}
      <div className="flex flex-wrap items-center gap-3">
        {sla !== null && (
          <p className={cn("text-sm font-semibold", slaColor)}>
            Must be resolved within {sla} day{sla !== 1 ? "s" : ""}
          </p>
        )}
        {intel.escalation_required && (
          <span className="rounded-full bg-red-600 px-3 py-0.5 text-xs font-bold text-white animate-pulse">
            ESCALATION REQUIRED
          </span>
        )}
      </div>

      {/* Stakeholders */}
      {intel.stakeholders.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Stakeholders</p>
          <div className="flex flex-wrap gap-2">
            {intel.stakeholders.map((s, i) => (
              <span key={i} className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
                <span className="h-5 w-5 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs">
                  {s.charAt(0).toUpperCase()}
                </span>
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Immediate actions */}
      {intel.immediate_actions.length > 0 && (
        <div>
          <h4 className="flex items-center gap-2 text-sm font-bold text-red-700 mb-3">
            <span className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
            Immediate Actions
          </h4>
          <div className="space-y-2">
            {intel.immediate_actions.map((a, i) => <ActionCard key={i} action={a} index={i} />)}
          </div>
        </div>
      )}

      {/* Sprint actions */}
      {intel.sprint_actions.length > 0 && (
        <div>
          <h4 className="flex items-center gap-2 text-sm font-bold text-amber-700 mb-3">
            <span className="h-2 w-2 rounded-full bg-amber-500" />
            This Sprint
          </h4>
          <div className="space-y-2">
            {intel.sprint_actions.map((a, i) => <ActionCard key={i} action={a} index={i} />)}
          </div>
        </div>
      )}

      {/* Quarterly actions */}
      {intel.quarterly_actions.length > 0 && (
        <div>
          <h4 className="flex items-center gap-2 text-sm font-bold text-green-700 mb-3">
            <span className="h-2 w-2 rounded-full bg-green-500" />
            This Quarter
          </h4>
          <div className="space-y-2">
            {intel.quarterly_actions.map((a, i) => <ActionCard key={i} action={a} index={i} />)}
          </div>
        </div>
      )}
    </div>
  );
}

function ImpactTab({ intel }: { intel: FindingIntelligence }) {
  const blastRadius = intel.blast_radius_count ?? 0;
  const factors = intel.causal_factors;
  const maxScore = Math.max(...factors.map(f => f.score), 0.01);

  // Simple SVG spider chart
  const N = factors.length;
  const SIZE = 120;
  const cx = SIZE / 2;
  const cy = SIZE / 2;
  const R = (SIZE / 2) * 0.8;

  function polarToXY(angleDeg: number, r: number) {
    const rad = ((angleDeg - 90) * Math.PI) / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  }

  const axes = factors.map((_, i) => (360 / N) * i);
  const dataPoints = factors.map((f, i) => {
    const pt = polarToXY(axes[i], R * (f.score / maxScore));
    return `${pt.x},${pt.y}`;
  });
  const gridPoints = axes.map(a => {
    const pt = polarToXY(a, R);
    return `${pt.x},${pt.y}`;
  });

  return (
    <div className="space-y-6">
      {/* Blast radius */}
      <div className="rounded-lg border border-slate-200 bg-slate-50 p-5 text-center">
        <p className="text-5xl font-black text-red-600">{blastRadius}</p>
        <p className="text-sm text-slate-600 mt-1">sensitive resources reachable</p>
      </div>

      {/* Radar chart */}
      {N >= 3 && (
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Risk Factor Spread</p>
          <div className="flex justify-center">
            <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} className="overflow-visible">
              {/* Grid rings */}
              {[0.25, 0.5, 0.75, 1].map((pct) => (
                <polygon
                  key={pct}
                  points={gridPoints.map((_, i) => {
                    const pt = polarToXY(axes[i], R * pct);
                    return `${pt.x},${pt.y}`;
                  }).join(" ")}
                  fill="none"
                  stroke="#e2e8f0"
                  strokeWidth="1"
                />
              ))}
              {/* Axes */}
              {axes.map((angle, i) => {
                const end = polarToXY(angle, R);
                return <line key={i} x1={cx} y1={cy} x2={end.x} y2={end.y} stroke="#e2e8f0" strokeWidth="1" />;
              })}
              {/* Data polygon */}
              {N >= 3 && (
                <polygon
                  points={dataPoints.join(" ")}
                  fill="rgba(239,68,68,0.25)"
                  stroke="#ef4444"
                  strokeWidth="2"
                />
              )}
              {/* Labels */}
              {factors.map((f, i) => {
                const labelPt = polarToXY(axes[i], R + 14);
                return (
                  <text key={i} x={labelPt.x} y={labelPt.y} textAnchor="middle" dominantBaseline="middle" fontSize="7" fill="#64748b">
                    {f.name.replace(/_/g, " ").slice(0, 10)}
                  </text>
                );
              })}
            </svg>
          </div>
        </div>
      )}

      {/* Secondary causes */}
      {intel.causal_chain.length > 1 && (
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Secondary Causes</p>
          <ul className="space-y-1">
            {intel.causal_chain.slice(1).map((cause, i) => (
              <li key={i} className="flex items-center gap-2 text-sm text-slate-700">
                <span className="h-1.5 w-1.5 rounded-full bg-amber-400 shrink-0" />
                <span className="capitalize">{cause.replace(/_/g, " ")}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ── Main Panel ────────────────────────────────────────────────────────────────

interface SecurityIntelligencePanelProps {
  findingId: string;
}

export default function SecurityIntelligencePanel({ findingId }: SecurityIntelligencePanelProps) {
  const { data: intel, error, isLoading, mutate } = useFindingIntelligence(findingId);
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [generating, setGenerating] = useState(false);

  async function handleGenerate() {
    setGenerating(true);
    try {
      await apiClient.post(`/api/v1/intelligence/findings/${findingId}`, {});
      await mutate();
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white">
      {/* Panel header */}
      <div className="flex items-center justify-between px-5 pt-5 pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2.5">
          <span className="text-sm font-bold text-slate-900">Security Intelligence</span>
          {intel?.rag_level && <RAGBadge level={intel.rag_level} size="sm" />}
        </div>
        {intel && intel.generation_status === "completed" && (
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="text-xs text-blue-600 hover:underline disabled:opacity-50"
          >
            Refresh Analysis
          </button>
        )}
      </div>

      {/* Loading skeleton */}
      {isLoading && (
        <div className="p-5 space-y-3">
          {[80, 60, 90, 50].map((w, i) => (
            <div key={i} className="h-3 rounded bg-slate-100 animate-pulse" style={{ width: `${w}%` }} />
          ))}
        </div>
      )}

      {/* Error state */}
      {error && !isLoading && (
        <div className="p-5 text-center space-y-3">
          <p className="text-sm text-slate-600">No intelligence analysis found for this finding.</p>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {generating && <Spinner className="h-3.5 w-3.5" />}
            {generating ? "Generating..." : "Generate Analysis"}
          </button>
        </div>
      )}

      {/* Pending state */}
      {!isLoading && !error && intel?.generation_status === "pending" && (
        <div className="flex flex-col items-center gap-3 p-10">
          <Spinner className="h-6 w-6 text-blue-500" />
          <p className="text-sm text-slate-600">Analysing with AI...</p>
        </div>
      )}

      {/* Completed state */}
      {!isLoading && !error && intel?.generation_status === "completed" && (
        <>
          {/* Tab bar */}
          <div className="flex border-b border-slate-100 px-5">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "py-3 px-1 mr-6 text-sm font-medium border-b-2 transition-colors",
                  activeTab === tab.id
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-slate-500 hover:text-slate-700"
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="p-5">
            {activeTab === "overview"        && <OverviewTab intel={intel} />}
            {activeTab === "rootcause"       && <RootCauseTab intel={intel} />}
            {activeTab === "recommendations" && <RecommendationsTab intel={intel} />}
            {activeTab === "impact"          && <ImpactTab intel={intel} />}
          </div>
        </>
      )}

      {/* Failed state */}
      {!isLoading && !error && intel?.generation_status === "failed" && (
        <div className="p-5 text-center space-y-3">
          <p className="text-sm text-red-600">Analysis generation failed.</p>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {generating ? "Retrying..." : "Retry Analysis"}
          </button>
        </div>
      )}

      {/* No intel yet (404 doesn't set error in all SWR configs) */}
      {!isLoading && !error && !intel && (
        <div className="p-5 text-center space-y-3">
          <p className="text-sm text-slate-600">No intelligence analysis found for this finding.</p>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {generating && <Spinner className="h-3.5 w-3.5" />}
            {generating ? "Generating..." : "Generate Analysis"}
          </button>
        </div>
      )}
    </div>
  );
}
