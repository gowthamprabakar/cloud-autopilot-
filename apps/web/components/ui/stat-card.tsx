"use client";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

const VARIANT_STYLES: Record<string, string> = {
  default: "bg-slate-800 border-slate-700/50",
  danger:  "bg-red-950/40 border-red-500/20",
  warning: "bg-orange-950/30 border-orange-500/20",
  success: "bg-green-950/30 border-green-500/20",
};

const ICON_COLORS: Record<string, string> = {
  default: "text-slate-400",
  danger:  "text-red-400",
  warning: "text-orange-400",
  success: "text-green-400",
};

const VALUE_COLORS: Record<string, string> = {
  default: "text-white",
  danger:  "text-red-300",
  warning: "text-orange-300",
  success: "text-green-300",
};

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: LucideIcon;
  variant?: "default" | "danger" | "warning" | "success";
  className?: string;
}

export function StatCard({ title, value, subtitle, icon: Icon, variant = "default", className }: StatCardProps) {
  return (
    <div className={cn("rounded-xl border p-4", VARIANT_STYLES[variant], className)}>
      <div className="flex items-center gap-2 mb-1">
        {Icon && <Icon className={cn("h-4 w-4", ICON_COLORS[variant])} />}
        <span className="text-xs text-slate-400">{title}</span>
      </div>
      <p className={cn("text-2xl font-bold", VALUE_COLORS[variant])}>{value}</p>
      {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
    </div>
  );
}
