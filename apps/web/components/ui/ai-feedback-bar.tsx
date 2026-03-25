"use client";
import { useState } from "react";
import { ThumbsUp, ThumbsDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface AIFeedbackBarProps {
  insightId: string;
  onFeedback?: (type: "helpful" | "unhelpful") => void;
  className?: string;
}

export function AIFeedbackBar({ insightId, onFeedback, className }: AIFeedbackBarProps) {
  const [feedback, setFeedback] = useState<"helpful" | "unhelpful" | null>(null);

  const handle = (type: "helpful" | "unhelpful") => {
    setFeedback(type);
    onFeedback?.(type);
  };

  return (
    <div className={cn("flex items-center gap-3 text-xs text-slate-400", className)}>
      <span>Was this helpful?</span>
      <button
        onClick={() => handle("helpful")}
        className={cn(
          "inline-flex items-center gap-1 rounded px-1.5 py-0.5 transition-colors",
          feedback === "helpful" ? "bg-green-500/20 text-green-400" : "hover:text-white hover:bg-slate-700"
        )}
      >
        <ThumbsUp className="h-3 w-3" />
        Yes
      </button>
      <button
        onClick={() => handle("unhelpful")}
        className={cn(
          "inline-flex items-center gap-1 rounded px-1.5 py-0.5 transition-colors",
          feedback === "unhelpful" ? "bg-red-500/20 text-red-400" : "hover:text-white hover:bg-slate-700"
        )}
      >
        <ThumbsDown className="h-3 w-3" />
        No
      </button>
    </div>
  );
}
