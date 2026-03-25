"use client";
import { cn } from "@/lib/utils";
import type { ScanStatus } from "@/lib/types";

interface ScanStatusBadgeProps {
  status: ScanStatus | null | undefined;
  /** ISO timestamp of when the last scan completed */
  completedAt?: string | null;
  className?: string;
}

function minutesAgo(iso: string): number {
  return Math.floor((Date.now() - new Date(iso).getTime()) / 60_000);
}

export function ScanStatusBadge({ status, completedAt, className }: ScanStatusBadgeProps) {
  if (!status) {
    return (
      <span className={cn("inline-flex items-center gap-1.5 text-xs text-slate-400", className)}>
        <span className="h-2 w-2 rounded-full bg-slate-300" />
        Never scanned
      </span>
    );
  }

  if (status === "running") {
    return (
      <span className={cn("inline-flex items-center gap-1.5 text-xs text-blue-600", className)}>
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-blue-500" />
        </span>
        Scanning...
      </span>
    );
  }

  if (status === "completed") {
    const mins = completedAt ? minutesAgo(completedAt) : null;
    const label =
      mins === null
        ? "Synced"
        : mins < 1
        ? "Synced just now"
        : mins === 1
        ? "Synced 1 min ago"
        : `Synced ${mins} min ago`;

    return (
      <span className={cn("inline-flex items-center gap-1.5 text-xs text-green-600", className)}>
        <svg className="h-3.5 w-3.5" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <circle cx="8" cy="8" r="7" className="stroke-green-500" strokeWidth="1.5" fill="none" />
          <path d="M5 8l2 2 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        {label}
      </span>
    );
  }

  if (status === "failed") {
    return (
      <span className={cn("inline-flex items-center gap-1.5 text-xs text-red-600", className)}>
        <svg className="h-3.5 w-3.5" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <circle cx="8" cy="8" r="7" className="stroke-red-500" strokeWidth="1.5" fill="none" />
          <path d="M5.5 5.5l5 5M10.5 5.5l-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
        Scan failed
      </span>
    );
  }

  if (status === "partial") {
    return (
      <span className={cn("inline-flex items-center gap-1.5 text-xs text-amber-600", className)}>
        <svg className="h-3.5 w-3.5" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path
            d="M8 2.5L14.5 13.5H1.5L8 2.5z"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinejoin="round"
            fill="none"
          />
          <path d="M8 7v3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          <circle cx="8" cy="11.5" r="0.75" fill="currentColor" />
        </svg>
        Partial scan
      </span>
    );
  }

  return null;
}
