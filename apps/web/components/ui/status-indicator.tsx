"use client";

/* ------------------------------------------------------------------ */
/*  Pulsing status orb                                                 */
/* ------------------------------------------------------------------ */

export type StatusLevel = "standby" | "initializing" | "running" | "certified" | "error";

interface StatusIndicatorProps {
  status: StatusLevel;
  label?: string;
}

const STATUS_CONFIG: Record<StatusLevel, { color: string; bg: string; pulse: boolean }> = {
  standby: { color: "#64748B", bg: "bg-slate-500", pulse: false },
  initializing: { color: "#FBBF24", bg: "bg-yellow-400", pulse: true },
  running: { color: "#3B82F6", bg: "bg-blue-500", pulse: true },
  certified: { color: "#22C55E", bg: "bg-green-500", pulse: false },
  error: { color: "#EF4444", bg: "bg-red-500", pulse: true },
};

export default function StatusIndicator({ status, label }: StatusIndicatorProps) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.standby;

  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="relative flex h-2.5 w-2.5">
        {cfg.pulse && (
          <span
            className={`absolute inset-0 rounded-full ${cfg.bg} opacity-75 animate-ping`}
          />
        )}
        <span
          className={`relative inline-flex h-2.5 w-2.5 rounded-full ${cfg.bg}`}
        />
      </span>
      {label && (
        <span className="text-[11px] font-medium capitalize" style={{ color: cfg.color }}>
          {label}
        </span>
      )}
    </span>
  );
}
