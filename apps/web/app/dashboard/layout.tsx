import { SidebarNav } from "@/components/shell/sidebar-nav";
import { NotificationsBell } from "@/components/shell/notifications-bell";

/**
 * Dashboard shell layout — wraps all /dashboard/* routes.
 * Provides the sidebar + main content area shell.
 */
export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <SidebarNav />
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex items-center justify-end gap-2 border-b border-slate-200 bg-white px-6 py-2.5 shrink-0">
          <NotificationsBell />
        </header>
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
