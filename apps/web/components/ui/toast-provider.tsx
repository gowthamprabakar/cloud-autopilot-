"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Info,
  X,
} from "lucide-react";

type ToastType = "success" | "error" | "warning" | "info";

interface Toast {
  id: string;
  message: string;
  type: ToastType;
  duration: number;
  exiting: boolean;
}

interface ToastContextValue {
  toast: (message: string, type?: ToastType, duration?: number) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const TOAST_ICONS: Record<ToastType, React.ReactNode> = {
  success: <CheckCircle2 className="h-5 w-5 text-green-400" />,
  error: <XCircle className="h-5 w-5 text-red-400" />,
  warning: <AlertTriangle className="h-5 w-5 text-amber-400" />,
  info: <Info className="h-5 w-5 text-blue-400" />,
};

const TOAST_BORDER_COLORS: Record<ToastType, string> = {
  success: "border-l-green-500",
  error: "border-l-red-500",
  warning: "border-l-amber-500",
  info: "border-l-blue-500",
};

let toastCounter = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timersRef = useRef<Map<string, NodeJS.Timeout>>(new Map());

  const removeToast = useCallback((id: string) => {
    // Start exit animation
    setToasts((prev) =>
      prev.map((t) => (t.id === id ? { ...t, exiting: true } : t))
    );
    // Remove after animation completes
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
      const timer = timersRef.current.get(id);
      if (timer) {
        clearTimeout(timer);
        timersRef.current.delete(id);
      }
    }, 300);
  }, []);

  const toast = useCallback(
    (message: string, type: ToastType = "info", duration: number = 4000) => {
      const id = `toast-${++toastCounter}`;
      const newToast: Toast = { id, message, type, duration, exiting: false };
      setToasts((prev) => [...prev, newToast]);

      const timer = setTimeout(() => removeToast(id), duration);
      timersRef.current.set(id, timer);
    },
    [removeToast]
  );

  // Cleanup timers on unmount
  useEffect(() => {
    const timers = timersRef.current;
    return () => {
      timers.forEach((timer) => clearTimeout(timer));
      timers.clear();
    };
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      {/* Toast container — fixed bottom-right */}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-3 pointer-events-none">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`pointer-events-auto flex w-80 items-start gap-3 rounded-lg border border-slate-700 border-l-4 bg-slate-800 p-4 shadow-lg transition-all duration-300 ${
              TOAST_BORDER_COLORS[t.type]
            } ${
              t.exiting
                ? "translate-x-full opacity-0"
                : "translate-x-0 opacity-100"
            }`}
            style={{
              animation: t.exiting ? undefined : "slideIn 0.3s ease-out",
            }}
          >
            <span className="mt-0.5 shrink-0">{TOAST_ICONS[t.type]}</span>
            <p className="flex-1 text-sm text-slate-200">{t.message}</p>
            <button
              onClick={() => removeToast(t.id)}
              className="shrink-0 rounded p-0.5 text-slate-400 transition-colors hover:text-slate-200"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
      {/* Inline keyframe for slide-in animation */}
      <style jsx global>{`
        @keyframes slideIn {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
      `}</style>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within a <ToastProvider>");
  }
  return ctx;
}
