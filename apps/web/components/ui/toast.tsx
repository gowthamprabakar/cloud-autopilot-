"use client";
/**
 * Minimal toast system — no external dependencies.
 * Usage:
 *   import { toast } from "@/components/ui/toast"
 *   toast.success("Done!")
 *   toast.error("Something broke")
 *
 * Mount <Toaster /> once in your layout (or wherever is convenient).
 */
import { useState, useEffect, useCallback, createContext, useContext } from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/utils";

type ToastVariant = "success" | "error" | "info";

interface ToastItem {
  id: number;
  message: string;
  variant: ToastVariant;
}

type ToastEmitter = {
  success: (msg: string) => void;
  error: (msg: string) => void;
  info: (msg: string) => void;
  _listeners: Set<(item: ToastItem) => void>;
  _subscribe: (fn: (item: ToastItem) => void) => () => void;
};

let _counter = 0;

export const toast: ToastEmitter = {
  _listeners: new Set(),
  _subscribe(fn) {
    this._listeners.add(fn);
    return () => this._listeners.delete(fn);
  },
  success(message) {
    const item: ToastItem = { id: ++_counter, message, variant: "success" };
    this._listeners.forEach((fn) => fn(item));
  },
  error(message) {
    const item: ToastItem = { id: ++_counter, message, variant: "error" };
    this._listeners.forEach((fn) => fn(item));
  },
  info(message) {
    const item: ToastItem = { id: ++_counter, message, variant: "info" };
    this._listeners.forEach((fn) => fn(item));
  },
};

const ICONS: Record<ToastVariant, React.ReactNode> = {
  success: (
    <svg className="h-4 w-4 shrink-0 text-green-500" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" fill="none" />
      <path d="M5 8l2 2 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  error: (
    <svg className="h-4 w-4 shrink-0 text-red-500" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" fill="none" />
      <path d="M5.5 5.5l5 5M10.5 5.5l-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  ),
  info: (
    <svg className="h-4 w-4 shrink-0 text-blue-500" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" fill="none" />
      <path d="M8 7v4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="8" cy="5.5" r="0.75" fill="currentColor" />
    </svg>
  ),
};

function ToastCard({ item, onDismiss }: { item: ToastItem; onDismiss: (id: number) => void }) {
  useEffect(() => {
    const t = setTimeout(() => onDismiss(item.id), 4_500);
    return () => clearTimeout(t);
  }, [item.id, onDismiss]);

  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-xl border bg-white px-4 py-3 shadow-lg text-sm text-slate-800 max-w-sm w-full",
        item.variant === "success" && "border-green-200",
        item.variant === "error" && "border-red-200",
        item.variant === "info" && "border-blue-200"
      )}
      role="alert"
    >
      {ICONS[item.variant]}
      <span className="flex-1 leading-5">{item.message}</span>
      <button
        onClick={() => onDismiss(item.id)}
        className="shrink-0 text-slate-400 hover:text-slate-600 transition-colors"
        aria-label="Dismiss"
      >
        <svg className="h-3.5 w-3.5" viewBox="0 0 14 14" fill="none" aria-hidden="true">
          <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </button>
    </div>
  );
}

export function Toaster() {
  const [items, setItems] = useState<ToastItem[]>([]);

  useEffect(() => {
    return toast._subscribe((item) => {
      setItems((prev) => [...prev, item]);
    });
  }, []);

  const dismiss = useCallback((id: number) => {
    setItems((prev) => prev.filter((t) => t.id !== id));
  }, []);

  if (typeof document === "undefined") return null;

  return createPortal(
    <div className="fixed bottom-6 right-6 z-[100] flex flex-col gap-2 items-end pointer-events-none">
      {items.map((item) => (
        <div key={item.id} className="pointer-events-auto">
          <ToastCard item={item} onDismiss={dismiss} />
        </div>
      ))}
    </div>,
    document.body
  );
}
