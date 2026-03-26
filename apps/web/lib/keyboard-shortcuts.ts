"use client";

import { useEffect } from "react";

/* ------------------------------------------------------------------ */
/*  Keyboard shortcut definitions                                      */
/* ------------------------------------------------------------------ */
export interface ShortcutAction {
  key: string;
  label: string;
  handler: () => void;
}

const INPUT_TAGS = new Set(["INPUT", "TEXTAREA", "SELECT"]);

/**
 * Global keyboard shortcuts hook.
 *
 * Built-in keys (override via `extra`):
 *  R = run, 1-6 = navigate tabs, F = fullscreen, E = export, S = spawn
 *
 * @param actions - map of key -> handler. Keys should be uppercase letters or digits.
 * @param enabled - master toggle (default true)
 */
export function useKeyboardShortcuts(
  actions: Record<string, () => void>,
  enabled = true,
) {
  useEffect(() => {
    if (!enabled) return;

    function handleKeyDown(e: KeyboardEvent) {
      // Skip when focused on form elements
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag && INPUT_TAGS.has(tag)) return;
      if ((e.target as HTMLElement)?.isContentEditable) return;

      // Skip if modifier keys are held (allow shortcuts to be unambiguous)
      if (e.ctrlKey || e.metaKey || e.altKey) return;

      const key = e.key.toUpperCase();
      const handler = actions[key];
      if (handler) {
        e.preventDefault();
        handler();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [actions, enabled]);
}

/* ------------------------------------------------------------------ */
/*  Default shortcut map factory                                       */
/* ------------------------------------------------------------------ */
export interface NavigationCallbacks {
  onRun?: () => void;
  onNavigate?: (tabIndex: number) => void;
  onFullscreen?: () => void;
  onExport?: () => void;
  onSpawn?: () => void;
  onHelp?: () => void;
}

export function buildDefaultShortcuts(cb: NavigationCallbacks): Record<string, () => void> {
  const map: Record<string, () => void> = {};

  if (cb.onRun) map["R"] = cb.onRun;
  if (cb.onNavigate) {
    for (let i = 1; i <= 6; i++) {
      const idx = i;
      map[String(idx)] = () => cb.onNavigate!(idx - 1);
    }
  }
  if (cb.onFullscreen) map["F"] = cb.onFullscreen;
  if (cb.onExport) map["E"] = cb.onExport;
  if (cb.onSpawn) map["S"] = cb.onSpawn;
  if (cb.onHelp) map["?"] = cb.onHelp;

  return map;
}
