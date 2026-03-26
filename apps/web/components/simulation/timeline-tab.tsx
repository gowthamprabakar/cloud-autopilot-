"use client";

import { useEffect, useRef, useState } from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */
export interface CommMessage {
  from_agent_id: string;
  to_agent_id: string;
  message_type: "info" | "solution" | "alert" | "spawn" | "wiz" | string;
  body: string;
  sequence_number: number;
  created_at: string;
}

interface TimelineTabProps {
  messages: CommMessage[];
}

/* ------------------------------------------------------------------ */
/*  Color maps                                                         */
/* ------------------------------------------------------------------ */
const TYPE_COLORS: Record<string, string> = {
  info: "#3B82F6",
  solution: "#22C55E",
  alert: "#EF4444",
  spawn: "#A855F7",
  wiz: "#F97316",
};

const AGENT_COLORS: Record<string, string> = {
  ORCH: "#FF6B35",
  SCOUT: "#00D4FF",
  EXPLOIT: "#FF3366",
  DEFEND: "#00FF88",
  VALID: "#FFD700",
  REPORT: "#9B59B6",
};

function agentColor(id: string): string {
  const upper = id.toUpperCase();
  for (const [key, color] of Object.entries(AGENT_COLORS)) {
    if (upper.includes(key)) return color;
  }
  return "#94A3B8";
}

function typeColor(type: string): string {
  return TYPE_COLORS[type] ?? "#94A3B8";
}

function formatTs(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return iso;
  }
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */
export default function TimelineTab({ messages }: TimelineTabProps) {
  const endRef = useRef<HTMLDivElement>(null);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  if (!messages.length) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-500 text-sm">
        No messages yet.
      </div>
    );
  }

  const sorted = [...messages].sort((a, b) => a.sequence_number - b.sequence_number);

  return (
    <div className="relative max-h-[600px] overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-slate-700">
      {/* Vertical spine */}
      <div className="absolute left-5 top-0 bottom-0 w-0.5 bg-slate-700" />

      <ul className="space-y-1">
        {sorted.map((msg, idx) => {
          const dotColor = typeColor(msg.message_type);
          const fromColor = agentColor(msg.from_agent_id);
          const toColor = agentColor(msg.to_agent_id);
          const expanded = expandedIdx === idx;

          return (
            <li key={idx} className="relative pl-12 pr-2 py-2 group">
              {/* Dot on spine */}
              <span
                className="absolute left-[14px] top-3 h-3 w-3 rounded-full border-2 border-slate-900 z-10"
                style={{ backgroundColor: dotColor }}
              />

              {/* Connector line */}
              <span className="absolute left-[19px] top-6 h-full w-0.5 bg-slate-800 group-last:hidden" />

              {/* Card */}
              <button
                type="button"
                onClick={() => setExpandedIdx(expanded ? null : idx)}
                className="w-full text-left rounded-lg bg-slate-900/60 border border-slate-800 hover:border-slate-600 transition-colors p-3"
              >
                {/* Header row */}
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-slate-500 font-mono">{formatTs(msg.created_at)}</span>
                  <span className="font-medium" style={{ color: fromColor }}>
                    {msg.from_agent_id}
                  </span>
                  <span className="text-slate-600">&rarr;</span>
                  <span className="font-medium" style={{ color: toColor }}>
                    {msg.to_agent_id}
                  </span>
                  <span
                    className="ml-auto text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded"
                    style={{ backgroundColor: `${dotColor}22`, color: dotColor }}
                  >
                    {msg.message_type}
                  </span>
                  <span className="text-slate-600 text-[10px]">#{msg.sequence_number}</span>
                </div>

                {/* Preview / expanded body */}
                <p className={`mt-1.5 text-xs text-slate-300 ${expanded ? "" : "line-clamp-2"}`}>
                  {msg.body}
                </p>

                {!expanded && msg.body.length > 140 && (
                  <span className="text-[10px] text-slate-500 mt-1 inline-block">
                    Click to expand
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ul>

      <div ref={endRef} />
    </div>
  );
}
