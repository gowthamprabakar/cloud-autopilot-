"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";

/* ------------------------------------------------------------------ */
/*  Shell components                                                    */
/* ------------------------------------------------------------------ */
import { SidebarNav } from "@/components/shell/sidebar-nav";
import TopBar from "@/components/shell/top-bar";
import { NotificationsBell } from "@/components/shell/notifications-bell";
import ShortcutHelp from "@/components/ui/shortcut-help";
import { ToastProvider } from "@/components/ui/toast-provider";

/* ------------------------------------------------------------------ */
/*  Keyboard shortcuts                                                  */
/* ------------------------------------------------------------------ */
import {
  useKeyboardShortcuts,
  buildDefaultShortcuts,
} from "@/lib/keyboard-shortcuts";

/* ------------------------------------------------------------------ */
/*  Dashboard nav tabs (keys 1-6)                                       */
/* ------------------------------------------------------------------ */
const QUICK_NAV = [
  "/dashboard",
  "/dashboard/executive",
  "/dashboard/simulations",
  "/dashboard/findings",
  "/dashboard/accounts",
  "/dashboard/settings",
] as const;

/* ------------------------------------------------------------------ */
/*  Layout                                                              */
/* ------------------------------------------------------------------ */

/**
 * Dashboard shell layout — wraps all /dashboard/* routes.
 * Provides a dark-themed three-part shell:
 *   Sidebar (left) | TopBar (top) + scrollable main content
 */
export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();

  /* ---- Keyboard shortcuts ---------------------------------------- */
  const shortcuts = useMemo(
    () =>
      buildDefaultShortcuts({
        onNavigate: (idx) => {
          if (idx < QUICK_NAV.length) router.push(QUICK_NAV[idx]);
        },
        onRun: () => router.push("/dashboard/simulations"),
        onFullscreen: () => document.documentElement.requestFullscreen?.(),
        onExport: () => router.push("/dashboard/export"),
        onHelp: () => {
          /* ShortcutHelp listens for "?" internally */
        },
      }),
    [router],
  );

  useKeyboardShortcuts(shortcuts);

  /* ---- Render ---------------------------------------------------- */
  return (
    <ToastProvider>
      <div className="flex h-screen bg-slate-950 text-slate-100">
        {/* Left sidebar */}
        <SidebarNav />

        {/* Main column */}
        <div className="flex flex-col flex-1 min-w-0">
          {/* Top bar with metrics + notifications */}
          <div className="relative">
            <TopBar />
            {/* Notification bell overlaid on the right side of the top bar */}
            <div className="absolute right-4 top-1/2 -translate-y-1/2 z-50">
              <NotificationsBell />
            </div>
          </div>

          {/* Scrollable page content */}
          <main className="flex-1 overflow-y-auto p-6">{children}</main>
        </div>

        {/* Global keyboard shortcut help overlay */}
        <ShortcutHelp />
      </div>
    </ToastProvider>
  );
}
