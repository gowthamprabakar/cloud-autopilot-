"use client";

import { useState, useCallback } from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */
export interface AgentOutput {
  agent_id: string;
  name: string;
  output: string;
  cost_usd: number;
}

interface AgentSolutionTabsProps {
  agents: AgentOutput[];
  onFullscreen?: (agent: AgentOutput) => void;
}

/* ------------------------------------------------------------------ */
/*  Agent color lookup                                                 */
/* ------------------------------------------------------------------ */
const AGENT_DOT: Record<string, string> = {
  ORCH: "#FF6B35",
  SCOUT: "#00D4FF",
  EXPLOIT: "#FF3366",
  DEFEND: "#00FF88",
  VALID: "#FFD700",
  REPORT: "#9B59B6",
};

function dotColor(name: string): string {
  const upper = name.toUpperCase();
  for (const [key, c] of Object.entries(AGENT_DOT)) {
    if (upper.includes(key)) return c;
  }
  return "#94A3B8";
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */
function exportMarkdown(agent: AgentOutput) {
  const blob = new Blob([`# ${agent.name}\n\n${agent.output}`], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${agent.agent_id}-solution.md`;
  a.click();
  URL.revokeObjectURL(url);
}

async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    /* fallback: ignore */
  }
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */
export default function AgentSolutionTabs({ agents, onFullscreen }: AgentSolutionTabsProps) {
  const [activeIdx, setActiveIdx] = useState(0);
  const active = agents[activeIdx] ?? null;

  const handleCopy = useCallback(() => {
    if (active) copyText(active.output);
  }, [active]);

  if (!agents.length) {
    return (
      <div className="flex items-center justify-center h-32 text-slate-500 text-sm">
        No agent solutions available.
      </div>
    );
  }

  return (
    <div className="flex flex-col rounded-xl border border-slate-800 bg-slate-950 overflow-hidden">
      {/* Tab bar */}
      <div className="flex items-center gap-1 px-3 pt-2 pb-0 overflow-x-auto scrollbar-thin scrollbar-thumb-slate-700 bg-slate-900/60">
        {agents.map((ag, idx) => {
          const isActive = idx === activeIdx;
          return (
            <button
              key={ag.agent_id}
              type="button"
              onClick={() => setActiveIdx(idx)}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-t-lg transition-colors whitespace-nowrap ${
                isActive
                  ? "bg-slate-950 text-white border border-b-0 border-slate-700"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
              }`}
            >
              <span
                className="inline-block h-2 w-2 rounded-full shrink-0"
                style={{ backgroundColor: dotColor(ag.name) }}
              />
              {ag.name}
            </button>
          );
        })}
      </div>

      {/* Toolbar */}
      {active && (
        <div className="flex items-center gap-2 px-4 py-2 border-b border-slate-800 bg-slate-900/40">
          {onFullscreen && (
            <button
              type="button"
              onClick={() => onFullscreen(active)}
              className="text-[11px] text-slate-400 hover:text-white px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 transition-colors"
            >
              Fullscreen
            </button>
          )}
          <button
            type="button"
            onClick={() => exportMarkdown(active)}
            className="text-[11px] text-slate-400 hover:text-white px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 transition-colors"
          >
            Export .md
          </button>
          <button
            type="button"
            onClick={handleCopy}
            className="text-[11px] text-slate-400 hover:text-white px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 transition-colors"
          >
            Copy
          </button>
        </div>
      )}

      {/* Output pane */}
      {active && (
        <div className="flex-1 overflow-auto max-h-[420px] p-4 scrollbar-thin scrollbar-thumb-slate-700">
          <pre className="text-xs text-slate-300 font-mono whitespace-pre-wrap leading-relaxed">
            <code>{active.output}</code>
          </pre>
        </div>
      )}

      {/* Footer */}
      {active && (
        <div className="flex items-center justify-between px-4 py-2 border-t border-slate-800 text-[11px] text-slate-500 bg-slate-900/40">
          <span>Agent: {active.agent_id}</span>
          <span>Cost: ${active.cost_usd.toFixed(4)}</span>
        </div>
      )}
    </div>
  );
}
