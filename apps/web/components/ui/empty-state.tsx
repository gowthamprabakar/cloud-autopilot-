"use client";
import { Loader2, AlertCircle, Inbox, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  variant: "empty" | "loading" | "error";
  title?: string;
  description?: string;
  icon?: LucideIcon;
  action?: { label: string; onClick: () => void };
  className?: string;
}

const DEFAULTS: Record<string, { title: string; description: string; Icon: LucideIcon }> = {
  empty:   { title: "No data", description: "Nothing to display yet.", Icon: Inbox },
  loading: { title: "Loading...", description: "Fetching data.", Icon: Loader2 },
  error:   { title: "Error", description: "Something went wrong.", Icon: AlertCircle },
};

export function EmptyState({ variant, title, description, icon, action, className }: EmptyStateProps) {
  const def = DEFAULTS[variant];
  const Icon = icon ?? def.Icon;

  return (
    <div className={cn("flex flex-col items-center justify-center py-16 text-center", className)}>
      <Icon
        className={cn(
          "h-10 w-10 mb-3",
          variant === "loading" && "animate-spin",
          variant === "error" ? "text-red-400" : "text-slate-500"
        )}
      />
      <p className="text-sm font-medium text-slate-300">{title ?? def.title}</p>
      <p className="text-xs text-slate-500 mt-1 max-w-xs">{description ?? def.description}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="mt-4 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-500 transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
