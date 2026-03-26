"use client";

import { useEffect, useCallback } from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */
interface FullscreenSolutionModalProps {
  isOpen: boolean;
  onClose: () => void;
  agentName: string;
  solution: string;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */
function exportMarkdown(name: string, solution: string) {
  const blob = new Blob([`# ${name}\n\n${solution}`], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${name.toLowerCase().replace(/\s+/g, "-")}-solution.md`;
  a.click();
  URL.revokeObjectURL(url);
}

async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    /* ignore */
  }
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */
export default function FullscreenSolutionModal({
  isOpen,
  onClose,
  agentName,
  solution,
}: FullscreenSolutionModalProps) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose],
  );

  useEffect(() => {
    if (!isOpen) return;
    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [isOpen, handleKeyDown]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />

      {/* Panel */}
      <div className="relative z-10 w-[90vw] max-w-5xl h-[85vh] flex flex-col rounded-2xl border border-slate-700 bg-slate-950 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
          <h2 className="text-sm font-semibold text-white tracking-wide">{agentName} &mdash; Solution</h2>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => exportMarkdown(agentName, solution)}
              className="text-[11px] text-slate-400 hover:text-white px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 transition-colors"
            >
              Export .md
            </button>
            <button
              type="button"
              onClick={() => copyText(solution)}
              className="text-[11px] text-slate-400 hover:text-white px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 transition-colors"
            >
              Copy
            </button>
            <button
              type="button"
              onClick={onClose}
              className="ml-2 text-slate-400 hover:text-white text-lg leading-none transition-colors"
              aria-label="Close"
            >
              &times;
            </button>
          </div>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto p-6 scrollbar-thin scrollbar-thumb-slate-700">
          <pre className="text-xs text-slate-300 font-mono whitespace-pre-wrap leading-relaxed">
            <code>{solution}</code>
          </pre>
        </div>
      </div>
    </div>
  );
}
