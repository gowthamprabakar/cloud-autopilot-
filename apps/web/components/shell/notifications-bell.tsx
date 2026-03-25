"use client";
import { useState, useRef, useEffect } from "react";
import { Bell } from "lucide-react";
import { cn } from "@/lib/utils";
import { useNotifications, markNotificationRead, markAllNotificationsRead } from "@/lib/hooks/use-notifications";
import type { Notification } from "@/lib/types";
import { useRouter } from "next/navigation";

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function NotificationsBell() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const { data, mutate } = useNotifications();

  // Close on outside click
  useEffect(() => {
    function handle(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, []);

  const unread = data?.unread_count ?? 0;
  const items = data?.items ?? [];

  async function handleClick(n: Notification) {
    if (!n.is_read) {
      await markNotificationRead(n.id);
      mutate();
    }
    setOpen(false);
    if (n.link_path) router.push(n.link_path as any);
  }

  async function handleMarkAll() {
    await markAllNotificationsRead();
    mutate();
  }

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        aria-label="Notifications"
      >
        <Bell className="h-4 w-4" />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 rounded-xl border border-slate-700 bg-slate-900 shadow-2xl z-50">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-700 px-4 py-3">
            <span className="text-sm font-semibold text-white">Notifications</span>
            {unread > 0 && (
              <button
                onClick={handleMarkAll}
                className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
              >
                Mark all read
              </button>
            )}
          </div>

          {/* Items */}
          <div className="max-h-80 overflow-y-auto divide-y divide-slate-800">
            {items.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-slate-500">
                No notifications
              </div>
            ) : (
              items.map((n) => (
                <button
                  key={n.id}
                  onClick={() => handleClick(n)}
                  className={cn(
                    "w-full text-left px-4 py-3 hover:bg-slate-800 transition-colors",
                    !n.is_read && "border-l-2 border-blue-500"
                  )}
                >
                  <p className={cn("text-sm font-medium", n.is_read ? "text-slate-300" : "text-white")}>
                    {n.title}
                  </p>
                  <p className="text-xs text-slate-400 mt-0.5 line-clamp-2">{n.body}</p>
                  <p className="text-xs text-slate-500 mt-1">{timeAgo(n.created_at)}</p>
                </button>
              ))
            )}
          </div>

          {/* Footer */}
          {items.length > 0 && (
            <div className="border-t border-slate-700 px-4 py-2">
              <button
                onClick={() => { setOpen(false); router.push("/dashboard/audit" as any); }}
                className="text-xs text-slate-400 hover:text-white transition-colors"
              >
                View audit log →
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
