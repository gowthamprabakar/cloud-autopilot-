"use client";

import { useEffect, useState } from "react";

/* ------------------------------------------------------------------ */
/*  Shortcut definitions                                               */
/* ------------------------------------------------------------------ */
const SHORTCUTS = [
  { key: "R", description: "Run simulation" },
  { key: "1-6", description: "Navigate tabs" },
  { key: "F", description: "Toggle fullscreen" },
  { key: "E", description: "Export solution" },
  { key: "S", description: "Spawn agent" },
  { key: "?", description: "Toggle this help" },
  { key: "Esc", description: "Close modal / overlay" },
];

/* ------------------------------------------------------------------ */
/*  Key badge                                                          */
/* ------------------------------------------------------------------ */
function KeyBadge({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="inline-flex items-center justify-center min-w-[28px] h-7 px-2 rounded-md bg-slate-800 border border-slate-600 text-xs font-mono font-semibold text-slate-200 shadow-sm">
      {children}
    </kbd>
  );
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */
export default function ShortcutHelp() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if ((e.target as HTMLElement)?.isContentEditable) return;

      if (e.key === "?" && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
      if (e.key === "Escape" && open) {
        setOpen(false);
      }
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={() => setOpen(false)} />

      {/* Panel */}
      <div className="relative z-10 w-full max-w-md rounded-2xl border border-slate-700 bg-slate-950 shadow-2xl p-6">
        <h2 className="text-sm font-semibold text-white mb-4">Keyboard Shortcuts</h2>

        <div className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-3">
          {SHORTCUTS.map((s) => (
            <div key={s.key} className="contents">
              <KeyBadge>{s.key}</KeyBadge>
              <span className="text-sm text-slate-300 self-center">{s.description}</span>
            </div>
          ))}
        </div>

        <button
          type="button"
          onClick={() => setOpen(false)}
          className="mt-5 w-full text-center text-xs text-slate-500 hover:text-slate-300 transition-colors"
        >
          Press <KeyBadge>?</KeyBadge> or click to close
        </button>
      </div>
    </div>
  );
}
