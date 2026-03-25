"use client";
import { cn } from "@/lib/utils";

interface TimestampLabelProps {
  date: string | Date;
  prefix?: string;
  className?: string;
}

function relative(d: Date): string {
  const now = Date.now();
  const diff = now - d.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export function TimestampLabel({ date, prefix, className }: TimestampLabelProps) {
  const d = typeof date === "string" ? new Date(date) : date;
  const label = relative(d);

  return (
    <span className={cn("text-xs text-slate-400", className)} title={d.toISOString()}>
      {prefix ? `${prefix} ` : ""}{label}
    </span>
  );
}
