"use client";
import { useState } from "react";
import { Brain, Eye, Target, Zap, Database, Shield, X, Star, ChevronDown, ChevronRight, DollarSign } from "lucide-react";
import { cn } from "@/lib/utils";

interface AgentAnatomyProps {
  agent: {
    agent_id: string; name: string; role: string; status: string; progress: number;
    autonomy_level: number; spawn_authority: boolean; output: string | null;
    working_memory: Record<string, any> | null; episodic_memory: string[] | null;
    goal_stack: string[] | null; input_tokens: number; output_tokens: number; cost_usd: number;
  };
  onClose: () => void;
}

const STATUS_COLOR: Record<string, string> = {
  idle: "bg-slate-600 text-slate-300", running: "bg-blue-600 text-blue-100 animate-pulse",
  done: "bg-green-600 text-green-100", error: "bg-red-600 text-red-100", spawning: "bg-purple-600 text-purple-100",
};

function Section({ icon: Icon, title, color, children, defaultOpen = false }: { icon: any; title: string; color: string; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-slate-700/50 rounded-lg overflow-hidden">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center gap-2 px-3 py-2 bg-slate-800/60 hover:bg-slate-800 transition-colors text-left">
        {open ? <ChevronDown className="h-3 w-3 text-slate-500" /> : <ChevronRight className="h-3 w-3 text-slate-500" />}
        <Icon className={cn("h-3.5 w-3.5", color)} />
        <span className="text-xs font-medium text-slate-300">{title}</span>
      </button>
      {open && <div className="px-3 py-2 bg-slate-900/40">{children}</div>}
    </div>
  );
}

export function AgentAnatomy({ agent, onClose }: AgentAnatomyProps) {
  const memory = agent.working_memory || {};
  const episodes = agent.episodic_memory || [];
  const goals = agent.goal_stack || [];

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-slate-900 border-l border-slate-700 shadow-2xl z-50 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm font-bold text-white">{agent.agent_id}</span>
          <span className="text-xs text-slate-400">{agent.name}</span>
          <span className={cn("rounded px-1.5 py-0.5 text-[10px] font-medium", STATUS_COLOR[agent.status] || STATUS_COLOR.idle)}>
            {agent.status}
          </span>
        </div>
        <button onClick={onClose} className="p-1 text-slate-500 hover:text-white"><X className="h-4 w-4" /></button>
      </div>

      {/* Meta bar */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-slate-700/50 text-[10px] text-slate-400">
        <span className="flex items-center gap-1">
          {[...Array(5)].map((_, i) => <Star key={i} className={cn("h-2.5 w-2.5", i < agent.autonomy_level ? "text-yellow-400 fill-yellow-400" : "text-slate-700")} />)}
        </span>
        {agent.spawn_authority && <span className="rounded bg-purple-600/20 text-purple-400 px-1.5 py-0.5">SPAWN</span>}
        <span className="ml-auto flex items-center gap-1"><DollarSign className="h-2.5 w-2.5" />{agent.cost_usd.toFixed(4)}</span>
        <span>{agent.input_tokens + agent.output_tokens} tokens</span>
      </div>

      {/* Anatomy sections */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        <Section icon={Brain} title="Working Memory" color="text-blue-400" defaultOpen>
          {Object.keys(memory).length === 0 ? (
            <p className="text-[11px] text-slate-500 italic">Empty</p>
          ) : (
            <div className="space-y-1">
              {Object.entries(memory).map(([k, v]) => (
                <div key={k} className="flex gap-2 text-[11px]">
                  <span className="font-medium text-blue-300 shrink-0">{k}:</span>
                  <span className="text-slate-300 font-mono truncate">{String(v)}</span>
                </div>
              ))}
            </div>
          )}
        </Section>

        <Section icon={Database} title="Episodic Memory" color="text-purple-400">
          {episodes.length === 0 ? (
            <p className="text-[11px] text-slate-500 italic">No episodes recorded</p>
          ) : (
            <div className="space-y-1">
              {[...episodes].reverse().map((ep, i) => (
                <div key={i} className="text-[11px] text-slate-300 flex gap-2">
                  <span className="text-purple-400/60 shrink-0">#{episodes.length - i}</span>
                  <span className="truncate">{ep}</span>
                </div>
              ))}
            </div>
          )}
        </Section>

        <Section icon={Target} title="Goal Stack" color="text-green-400">
          {goals.length === 0 ? (
            <p className="text-[11px] text-slate-500 italic">No goals set</p>
          ) : (
            <div className="space-y-1">
              {goals.map((g, i) => (
                <div key={i} className="text-[11px] flex gap-2">
                  <span className={cn("shrink-0 rounded px-1 py-0.5 text-[9px] font-bold",
                    i === 0 ? "bg-red-600/20 text-red-400" : i === 1 ? "bg-orange-600/20 text-orange-400" : "bg-slate-700 text-slate-400"
                  )}>P{i + 1}</span>
                  <span className="text-slate-300">{g}</span>
                </div>
              ))}
            </div>
          )}
        </Section>

        <Section icon={Eye} title="Perception Feeds" color="text-orange-400">
          <div className="flex flex-wrap gap-1">
            {["comm_bus", "Security Graph", "prior_agent_outputs", "gate_states"].map(feed => (
              <span key={feed} className="rounded bg-orange-600/10 text-orange-300 border border-orange-500/20 px-1.5 py-0.5 text-[10px]">{feed}</span>
            ))}
          </div>
        </Section>

        <Section icon={Zap} title="Action Loop" color="text-red-400">
          <div className="flex items-center gap-1 py-1">
            {["SENSE", "THINK", "PLAN", "ACT"].map((step, i) => (
              <div key={step} className="flex items-center gap-1">
                <span className={cn("rounded px-2 py-1 text-[10px] font-bold transition-colors",
                  agent.status === "running" ? "bg-red-600/20 text-red-300 animate-pulse" : agent.status === "done" ? "bg-green-600/20 text-green-300" : "bg-slate-800 text-slate-500"
                )}>{step}</span>
                {i < 3 && <span className="text-slate-600 text-[10px]">→</span>}
              </div>
            ))}
          </div>
        </Section>

        <Section icon={Shield} title="Agent Output" color="text-white" defaultOpen={agent.status === "done"}>
          {agent.output ? (
            <pre className="text-[11px] text-slate-300 whitespace-pre-wrap font-mono leading-relaxed max-h-80 overflow-y-auto">{agent.output}</pre>
          ) : (
            <p className="text-[11px] text-slate-500 italic">No output yet</p>
          )}
        </Section>
      </div>
    </div>
  );
}
