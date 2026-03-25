"use client";
import { cn } from "@/lib/utils";
import type { AttackPath, SecurityGraphStats } from "@/lib/types";

interface Props {
  attackPaths: AttackPath[];
  selectedPathId: string | null;
  onSelectPath: (pathId: string | null) => void;
  graphStats: SecurityGraphStats | null;
}

function SeverityBadge({ severity }: { severity: string }) {
  const s = severity.toLowerCase();
  const cls =
    s === "critical" ? "bg-red-100 text-red-700" :
    s === "high"     ? "bg-orange-100 text-orange-700" :
    s === "medium"   ? "bg-amber-100 text-amber-700" :
                       "bg-slate-100 text-slate-600";
  return (
    <span className={cn("rounded-full px-2 py-0.5 text-xs font-semibold capitalize", cls)}>
      {severity}
    </span>
  );
}

function StatBox({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center rounded-lg bg-slate-50 py-2 px-1 min-w-0">
      <span className={cn("text-lg font-black leading-none", color)}>{value}</span>
      <span className="text-xs text-slate-500 text-center leading-tight mt-0.5">{label}</span>
    </div>
  );
}

export default function AttackPathSidebar({ attackPaths, selectedPathId, onSelectPath, graphStats }: Props) {
  return (
    <aside className="flex w-72 shrink-0 flex-col bg-white border-r border-slate-200 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
        <h2 className="text-sm font-bold text-slate-900">Attack Paths</h2>
        {attackPaths.length > 0 && (
          <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-bold text-red-700">
            {attackPaths.length}
          </span>
        )}
      </div>

      {/* Stats strip */}
      {graphStats && (
        <div className="flex gap-1.5 px-3 py-2 border-b border-slate-100">
          <StatBox label="Nodes"       value={graphStats.total_nodes}        color="text-slate-700" />
          <StatBox label="Attack Path" value={graphStats.attack_path_nodes}  color="text-red-600"   />
          <StatBox label="Internet"    value={graphStats.internet_facing}    color="text-orange-600"/>
          <StatBox label="Sensitive"   value={graphStats.sensitive_data_nodes} color="text-purple-600"/>
        </div>
      )}

      {/* List */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-2">
        {attackPaths.length === 0 && (
          <div className="flex flex-col items-center justify-center h-40 gap-2 text-slate-400">
            <span className="text-3xl">✅</span>
            <p className="text-xs text-center leading-relaxed">
              No attack paths detected.<br />
              Seed demo data to see an example.
            </p>
          </div>
        )}

        {attackPaths.map((path) => {
          const isSelected = path.id === selectedPathId;
          return (
            <button
              key={path.id}
              onClick={() => onSelectPath(isSelected ? null : path.id)}
              className={cn(
                "w-full rounded-lg border p-3 text-left transition-all hover:border-slate-300 hover:shadow-sm",
                isSelected
                  ? "border-red-300 bg-red-50 shadow-sm"
                  : "border-slate-200 bg-white"
              )}
            >
              {/* Top row */}
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <SeverityBadge severity={path.severity} />
                {path.is_active && (
                  <span className="h-2 w-2 rounded-full bg-red-500 animate-pulse shrink-0" />
                )}
              </div>

              {/* Path name */}
              <p className="text-xs font-semibold text-slate-800 leading-snug mb-1">{path.name}</p>

              {/* Entry → Target */}
              {(path.entry_description || path.target_description) && (
                <div className="flex items-center gap-1 text-xs text-slate-500 mb-2">
                  <span className="truncate">{path.entry_description ?? "Entry"}</span>
                  <span className="shrink-0">→</span>
                  <span className="truncate">{path.target_description ?? "Target"}</span>
                </div>
              )}

              {/* Blast radius */}
              <p className="text-xs text-slate-600 mb-1.5">
                💥 Blast radius: <span className="font-semibold">{path.blast_radius}</span>
              </p>

              {/* Toxic combo tags */}
              {path.toxic_combo_tags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {path.toxic_combo_tags.slice(0, 4).map((tag, i) => (
                    <span key={i} className="rounded bg-red-100 px-1.5 py-0.5 text-xs text-red-700 font-medium">
                      {tag}
                    </span>
                  ))}
                  {path.toxic_combo_tags.length > 4 && (
                    <span className="text-xs text-slate-400">+{path.toxic_combo_tags.length - 4}</span>
                  )}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </aside>
  );
}
