"use client";
import { cn } from "@/lib/utils";

const COLORS: Record<string, string> = {
  critical: "bg-red-500/15 text-red-400 border-red-500/30",
  high: "bg-orange-500/15 text-orange-400 border-orange-500/30",
  medium: "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
  low: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  info: "bg-slate-500/15 text-slate-400 border-slate-500/30",
};

interface SeverityBadgeProps {
  severity: "critical" | "high" | "medium" | "low" | "info";
  size?: "sm" | "md";
  className?: string;
}

export function SeverityBadge({ severity, size = "sm", className }: SeverityBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded border font-medium capitalize",
        size === "sm" ? "px-1.5 py-0.5 text-[10px]" : "px-2 py-0.5 text-xs",
        COLORS[severity] ?? COLORS.info,
        className
      )}
    >
      {severity}
    </span>
  );
}
