"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Shield,
  LayoutDashboard,
  LogOut,
  Settings,
  ChevronDown,
  ChevronRight,
  Network,
  Atom,
  Brain,
  Cpu,
  CloudCog,
  PanelLeftClose,
  PanelLeft,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/hooks/use-auth";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface NavItem {
  href: string;
  label: string;
  exact?: boolean;
  roles?: string[];
}

interface NavGroup {
  id: string;
  label: string;
  icon: LucideIcon;
  defaultCollapsed?: boolean;
  items: NavItem[];
}

/* ------------------------------------------------------------------ */
/*  Navigation structure                                               */
/* ------------------------------------------------------------------ */

const NAV_GROUPS: NavGroup[] = [
  {
    id: "overview",
    label: "Overview",
    icon: LayoutDashboard,
    items: [
      { href: "/dashboard", label: "Dashboard", exact: true },
      { href: "/dashboard/executive", label: "Executive", roles: ["admin", "super_admin"] },
      { href: "/dashboard/portfolio", label: "Portfolio", roles: ["admin", "super_admin"] },
    ],
  },
  {
    id: "simulation",
    label: "Simulation",
    icon: Atom,
    items: [
      { href: "/dashboard/simulations", label: "Simulations", roles: ["admin", "super_admin", "analyst"] },
      { href: "/dashboard/modules", label: "Modules", roles: ["admin", "super_admin", "analyst"] },
      { href: "/dashboard/wiz-coverage", label: "Wiz Coverage", roles: ["admin", "super_admin", "analyst"] },
      { href: "/dashboard/gap-domains", label: "Gap Domains", roles: ["admin", "super_admin", "analyst"] },
    ],
  },
  {
    id: "security",
    label: "Security",
    icon: Shield,
    items: [
      { href: "/dashboard/findings", label: "Findings" },
      { href: "/dashboard/cspm", label: "CSPM", roles: ["admin", "super_admin", "analyst"] },
      { href: "/dashboard/ciem", label: "CIEM", roles: ["admin", "super_admin", "analyst"] },
      { href: "/dashboard/detections", label: "Detections", roles: ["admin", "super_admin", "analyst"] },
      { href: "/dashboard/vulns", label: "Vulns", roles: ["admin", "super_admin", "analyst"] },
      { href: "/dashboard/mitre", label: "MITRE ATT&CK", roles: ["admin", "super_admin", "analyst"] },
    ],
  },
  {
    id: "graph",
    label: "Graph & Analysis",
    icon: Network,
    items: [
      { href: "/dashboard/security-graph", label: "Security Graph", roles: ["admin", "super_admin", "analyst"] },
      { href: "/dashboard/graph-explorer", label: "Graph Explorer", roles: ["admin", "super_admin", "analyst"] },
      { href: "/dashboard/attack-paths", label: "Attack Paths", roles: ["admin", "super_admin", "analyst"] },
      { href: "/dashboard/drift", label: "Drift", roles: ["admin", "super_admin", "analyst"] },
    ],
  },
  {
    id: "agent",
    label: "Agent Intelligence",
    icon: Brain,
    items: [
      { href: "/dashboard/agent-memory", label: "Agent Memory", roles: ["admin", "super_admin", "analyst"] },
      { href: "/dashboard/audit-trail", label: "Sim Audit", roles: ["admin", "super_admin"] },
      { href: "/dashboard/session-history", label: "Sim History", roles: ["admin", "super_admin", "analyst"] },
    ],
  },
  {
    id: "modules",
    label: "Modules",
    icon: Cpu,
    defaultCollapsed: true,
    items: [
      { href: "/dashboard/modules/cwpp", label: "CWPP", roles: ["admin", "super_admin", "analyst"] },
      { href: "/dashboard/modules/dspm", label: "DSPM", roles: ["admin", "super_admin", "analyst"] },
      { href: "/dashboard/modules/kspm", label: "KSPM", roles: ["admin", "super_admin", "analyst"] },
      { href: "/dashboard/modules/asm", label: "ASM", roles: ["admin", "super_admin", "analyst"] },
      { href: "/dashboard/modules/quantum", label: "Quantum", roles: ["admin", "super_admin", "analyst"] },
      { href: "/dashboard/modules/deepfake", label: "Deepfake", roles: ["admin", "super_admin", "analyst"] },
      { href: "/dashboard/modules/supply-chain", label: "Supply Chain", roles: ["admin", "super_admin", "analyst"] },
      { href: "/dashboard/modules/ot-ics", label: "OT/ICS", roles: ["admin", "super_admin", "analyst"] },
      { href: "/dashboard/modules/llmjacking", label: "LLMjacking", roles: ["admin", "super_admin", "analyst"] },
      { href: "/dashboard/modules/fedid", label: "FedID", roles: ["admin", "super_admin", "analyst"] },
    ],
  },
  {
    id: "infrastructure",
    label: "Infrastructure",
    icon: CloudCog,
    items: [
      { href: "/dashboard/accounts", label: "AWS Accounts" },
      { href: "/dashboard/compliance", label: "Compliance" },
      { href: "/dashboard/remediation", label: "Remediation" },
      { href: "/dashboard/suppression", label: "Suppression" },
      { href: "/dashboard/reports", label: "Reports" },
      { href: "/dashboard/exports", label: "Exports", roles: ["admin", "super_admin", "analyst"] },
    ],
  },
  {
    id: "settings",
    label: "Settings",
    icon: Settings,
    defaultCollapsed: true,
    items: [
      { href: "/dashboard/settings", label: "General", exact: true },
      { href: "/dashboard/settings/api-keys", label: "API Keys", roles: ["admin", "super_admin"] },
      { href: "/dashboard/settings/webhooks", label: "Webhooks", roles: ["admin", "super_admin"] },
      { href: "/dashboard/settings/workspace", label: "Workspace", roles: ["admin", "super_admin"] },
      { href: "/dashboard/settings/tenant", label: "Tenant Admin", roles: ["admin", "super_admin"] },
      { href: "/dashboard/settings/integrations", label: "Integrations", roles: ["admin", "super_admin"] },
      { href: "/dashboard/settings/integration-hub", label: "Integration Hub", roles: ["admin", "super_admin"] },
      { href: "/dashboard/settings/email", label: "Email" },
      { href: "/dashboard/settings/prompts", label: "AI Prompts", roles: ["admin", "super_admin"] },
      { href: "/dashboard/settings/simulation", label: "Sim Config", roles: ["admin", "super_admin"] },
      { href: "/dashboard/settings/security", label: "Security" },
      { href: "/dashboard/settings/reports", label: "Scheduled Reports", roles: ["admin", "super_admin"] },
    ],
  },
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const STORAGE_KEY = "omnisec:sidebar-collapsed";

function isItemActive(href: string, pathname: string, exact?: boolean) {
  return exact ? pathname === href : pathname.startsWith(href);
}

function groupHasActiveItem(group: NavGroup, pathname: string) {
  return group.items.some((item) => isItemActive(item.href, pathname, item.exact));
}

function canSeeItem(item: NavItem, role: string | undefined) {
  if (!item.roles) return true;
  if (!role) return false;
  return item.roles.includes(role);
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function SidebarNav() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  // ---------- sidebar collapse ----------
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === "true") setCollapsed(true);
    } catch {
      // SSR or storage unavailable
    }
  }, []);

  const toggleCollapsed = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(STORAGE_KEY, String(next));
      } catch {
        // ignore
      }
      return next;
    });
  }, []);

  // ---------- group expand/collapse ----------
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    NAV_GROUPS.forEach((g) => {
      initial[g.id] = !g.defaultCollapsed;
    });
    return initial;
  });

  // Auto-expand the group that contains the active item
  useEffect(() => {
    NAV_GROUPS.forEach((group) => {
      if (groupHasActiveItem(group, pathname)) {
        setExpandedGroups((prev) => {
          if (prev[group.id]) return prev;
          return { ...prev, [group.id]: true };
        });
      }
    });
  }, [pathname]);

  const toggleGroup = useCallback((groupId: string) => {
    setExpandedGroups((prev) => ({ ...prev, [groupId]: !prev[groupId] }));
  }, []);

  // ---------- render ----------
  return (
    <aside
      className={cn(
        "flex flex-col bg-slate-900 border-r border-slate-800 transition-all duration-200",
        collapsed ? "w-16" : "w-60"
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-4 py-4 border-b border-slate-800 min-h-[57px]">
        <Shield className="h-5 w-5 text-blue-400 shrink-0" />
        {!collapsed && (
          <span className="font-semibold text-sm text-white truncate">
            OmniSec
          </span>
        )}
      </div>

      {/* Nav groups */}
      <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-1">
        {NAV_GROUPS.map((group) => {
          const visibleItems = group.items.filter((item) =>
            canSeeItem(item, user?.role)
          );
          if (visibleItems.length === 0) return null;

          const isExpanded = expandedGroups[group.id] ?? false;
          const hasActive = groupHasActiveItem(group, pathname);
          const GroupIcon = group.icon;

          return (
            <div key={group.id}>
              {/* Group header */}
              <button
                onClick={() => {
                  if (collapsed) {
                    setCollapsed(false);
                    try {
                      localStorage.setItem(STORAGE_KEY, "false");
                    } catch {
                      // ignore
                    }
                    setExpandedGroups((prev) => ({ ...prev, [group.id]: true }));
                  } else {
                    toggleGroup(group.id);
                  }
                }}
                title={collapsed ? group.label : undefined}
                className={cn(
                  "flex w-full items-center rounded-lg px-3 py-2 text-xs font-semibold uppercase tracking-wider transition-colors",
                  hasActive
                    ? "text-blue-400"
                    : "text-slate-500 hover:text-slate-300",
                  collapsed && "justify-center"
                )}
              >
                <GroupIcon className="h-4 w-4 shrink-0" />
                {!collapsed && (
                  <>
                    <span className="ml-3 flex-1 text-left">{group.label}</span>
                    {isExpanded ? (
                      <ChevronDown className="h-3.5 w-3.5 text-slate-600" />
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5 text-slate-600" />
                    )}
                  </>
                )}
              </button>

              {/* Group items */}
              {!collapsed && isExpanded && (
                <div className="mt-0.5 ml-3 space-y-0.5">
                  {visibleItems.map((item) => {
                    const active = isItemActive(item.href, pathname, item.exact);
                    return (
                      <Link
                        key={item.href}
                        href={item.href as any}
                        className={cn(
                          "flex items-center rounded-md px-3 py-1.5 text-sm transition-colors",
                          active
                            ? "bg-blue-600/20 text-blue-400 font-medium"
                            : "text-slate-400 hover:text-white hover:bg-slate-800"
                        )}
                      >
                        <span className="w-1.5 h-1.5 rounded-full mr-3 shrink-0"
                          style={{
                            backgroundColor: active
                              ? "rgb(96 165 250)" // blue-400
                              : "rgb(71 85 105)",  // slate-600
                          }}
                        />
                        {item.label}
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      {/* User footer */}
      <div className="border-t border-slate-800 px-2 py-3 space-y-1">
        {user && !collapsed && (
          <div className="px-3 py-1.5">
            <p className="text-xs font-medium text-white truncate">
              {user.full_name}
            </p>
            <p className="text-xs text-slate-500 truncate">{user.email}</p>
          </div>
        )}
        <button
          onClick={logout}
          title={collapsed ? "Sign out" : undefined}
          className={cn(
            "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-400 hover:text-white hover:bg-slate-800 transition-colors",
            collapsed && "justify-center"
          )}
        >
          <LogOut className="h-4 w-4 shrink-0" />
          {!collapsed && "Sign out"}
        </button>

        {/* Collapse toggle */}
        <button
          onClick={toggleCollapsed}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className={cn(
            "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-400 hover:text-white hover:bg-slate-800 transition-colors",
            collapsed && "justify-center"
          )}
        >
          {collapsed ? (
            <PanelLeft className="h-4 w-4 shrink-0" />
          ) : (
            <>
              <PanelLeftClose className="h-4 w-4 shrink-0" />
              <span>Collapse</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
