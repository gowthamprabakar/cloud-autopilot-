"use client";
import { cn } from "@/lib/utils";
import type { RAGLevel } from "@/lib/types";

interface RAGBadgeProps {
  level: RAGLevel;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}

const LEVEL_CONFIG: Record<RAGLevel, { bg: string; label: string; dot: string }> = {
  RED:   { bg: "bg-red-600",   label: "Critical",      dot: "bg-red-500" },
  AMBER: { bg: "bg-amber-500", label: "High Priority",  dot: "bg-amber-400" },
  GREEN: { bg: "bg-green-600", label: "Low Priority",   dot: "bg-green-500" },
};

const SIZE_CONFIG = {
  sm: "px-1.5 py-0.5 text-xs",
  md: "px-2.5 py-1 text-sm",
  lg: "px-3.5 py-1.5 text-base",
};

export function RAGBadge({ level, size = "md", showLabel = true }: RAGBadgeProps) {
  const cfg = LEVEL_CONFIG[level];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full font-semibold text-white",
        cfg.bg,
        SIZE_CONFIG[size],
        level === "RED" && "animate-pulse"
      )}
    >
      <span className={cn("rounded-full", size === "sm" ? "h-1.5 w-1.5" : "h-2 w-2", cfg.dot)} />
      {showLabel && cfg.label}
    </span>
  );
}

interface RAGIndicatorBarProps {
  activeLevel: RAGLevel;
}

export function RAGIndicatorBar({ activeLevel }: RAGIndicatorBarProps) {
  const levels: RAGLevel[] = ["RED", "AMBER", "GREEN"];
  const labelMap: Record<RAGLevel, string> = {
    RED:   "Immediate",
    AMBER: "This Sprint",
    GREEN: "This Quarter",
  };
  const bgMap: Record<RAGLevel, string> = {
    RED:   "bg-red-600 text-white",
    AMBER: "bg-amber-500 text-white",
    GREEN: "bg-green-600 text-white",
  };
  const inactiveBgMap: Record<RAGLevel, string> = {
    RED:   "bg-red-100 text-red-700",
    AMBER: "bg-amber-100 text-amber-700",
    GREEN: "bg-green-100 text-green-700",
  };

  return (
    <div className="flex rounded-lg overflow-hidden border border-slate-200">
      {levels.map((level) => {
        const isActive = level === activeLevel;
        return (
          <div
            key={level}
            className={cn(
              "flex-1 text-center py-2 text-xs font-semibold transition-colors",
              isActive ? bgMap[level] : inactiveBgMap[level]
            )}
          >
            {level} — {labelMap[level]}
          </div>
        );
      })}
    </div>
  );
}
