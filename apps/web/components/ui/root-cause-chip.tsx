"use client";
import { cn } from "@/lib/utils";
import { ShieldAlert, Key, Globe, Lock, CheckSquare, HelpCircle } from "lucide-react";

const CAUSE_MAP: Record<string, { color: string; Icon: typeof ShieldAlert }> = {
  misconfiguration: { color: "bg-orange-500/15 text-orange-400 border-orange-500/30", Icon: ShieldAlert },
  identity:         { color: "bg-purple-500/15 text-purple-400 border-purple-500/30", Icon: Key },
  iam:              { color: "bg-purple-500/15 text-purple-400 border-purple-500/30", Icon: Key },
  exposure:         { color: "bg-red-500/15 text-red-400 border-red-500/30", Icon: Globe },
  public:           { color: "bg-red-500/15 text-red-400 border-red-500/30", Icon: Globe },
  encryption:       { color: "bg-blue-500/15 text-blue-400 border-blue-500/30", Icon: Lock },
  compliance:       { color: "bg-green-500/15 text-green-400 border-green-500/30", Icon: CheckSquare },
};

interface RootCauseChipProps {
  cause: string;
  className?: string;
}

export function RootCauseChip({ cause, className }: RootCauseChipProps) {
  const key = cause.toLowerCase();
  const match = Object.entries(CAUSE_MAP).find(([k]) => key.includes(k));
  const { color, Icon } = match?.[1] ?? { color: "bg-slate-500/15 text-slate-400 border-slate-500/30", Icon: HelpCircle };

  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium", color, className)}>
      <Icon className="h-2.5 w-2.5" />
      {cause}
    </span>
  );
}
