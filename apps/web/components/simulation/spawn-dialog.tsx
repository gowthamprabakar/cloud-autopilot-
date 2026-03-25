"use client";
import { useState } from "react";
import { Zap, X } from "lucide-react";
import { cn } from "@/lib/utils";

const AGENT_TYPES = [
  { id: "DEEP-XX", name: "DeepDiver", role: "Deep analysis", sigil: "🔬" },
  { id: "QUANT-01", name: "QuantumSage", role: "Quantum specialist", sigil: "⚛" },
  { id: "FAKE-01", name: "DeepFakeHunter", role: "Identity fraud", sigil: "🎭" },
  { id: "CHAIN-01", name: "ChainBreaker", role: "Supply chain", sigil: "🔗" },
  { id: "OT-01", name: "SCADAGuard", role: "OT/ICS specialist", sigil: "🏭" },
  { id: "LLM-01", name: "LLMShield", role: "LLMjacking", sigil: "🤖" },
  { id: "WIZ-CSPM", name: "CSPMAgent", role: "Posture management", sigil: "🔧" },
  { id: "WIZ-CIEM", name: "CIEMAgent", role: "Entitlement mgmt", sigil: "🔑" },
  { id: "WIZ-CDR", name: "CDRAgent", role: "Detection & response", sigil: "📡" },
  { id: "WIZ-DSPM", name: "DSPMAgent", role: "Data security", sigil: "💾" },
  { id: "WIZ-KSPM", name: "KSPMAgent", role: "K8s security", sigil: "☸" },
  { id: "WIZ-IaC", name: "IaCAgent", role: "Code security", sigil: "📝" },
  { id: "WIZ-UVM", name: "UVMAgent", role: "Vuln management", sigil: "🐛" },
  { id: "WIZ-AISPM", name: "AISPMAgent", role: "AI security", sigil: "🧠" },
  { id: "WIZ-ASM", name: "ASMAgent", role: "Attack surface", sigil: "🌐" },
];

interface SpawnDialogProps {
  runId: string;
  onSpawn: (agentType: string, customPrompt?: string) => Promise<void>;
  onClose: () => void;
}

export function SpawnDialog({ runId, onSpawn, onClose }: SpawnDialogProps) {
  const [agentType, setAgentType] = useState("DEEP-XX");
  const [customPrompt, setCustomPrompt] = useState("");
  const [spawning, setSpawning] = useState(false);

  const handleSpawn = async () => {
    setSpawning(true);
    try {
      await onSpawn(agentType, customPrompt || undefined);
      onClose();
    } catch {
      setSpawning(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-md shadow-2xl" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4 text-purple-400" />
            <h2 className="text-sm font-semibold text-white">Spawn Specialist Agent</h2>
          </div>
          <button onClick={onClose} className="p-1 text-slate-500 hover:text-white"><X className="h-4 w-4" /></button>
        </div>

        <div className="p-5 space-y-4">
          {/* Agent type selector */}
          <div>
            <label className="text-xs font-medium text-slate-400 mb-1.5 block">Agent Type</label>
            <select
              value={agentType}
              onChange={e => setAgentType(e.target.value)}
              className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-white focus:outline-none focus:border-purple-500"
            >
              {AGENT_TYPES.map(a => (
                <option key={a.id} value={a.id}>{a.sigil} {a.name} — {a.role}</option>
              ))}
            </select>
          </div>

          {/* Custom prompt */}
          <div>
            <label className="text-xs font-medium text-slate-400 mb-1.5 block">Custom Prompt (optional)</label>
            <textarea
              value={customPrompt}
              onChange={e => setCustomPrompt(e.target.value)}
              placeholder="Override the default system prompt for this agent..."
              rows={4}
              className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-purple-500 resize-none font-mono"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={handleSpawn}
              disabled={spawning}
              className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-purple-600 hover:bg-purple-500 disabled:opacity-50 px-4 py-2.5 text-sm font-medium text-white transition-colors"
            >
              <Zap className="h-3.5 w-3.5" />
              {spawning ? "Spawning..." : "Spawn Agent"}
            </button>
            <button onClick={onClose} className="rounded-lg border border-slate-600 px-4 py-2.5 text-sm text-slate-400 hover:text-white transition-colors">
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
