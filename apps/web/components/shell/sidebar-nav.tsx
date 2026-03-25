"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Shield, LayoutDashboard, AlertTriangle, CloudCog,
  CheckSquare, LogOut, Settings, ChevronRight, Users2, ClipboardList,
  ShieldOff, BarChart3, KeyRound, Webhook, ClipboardCheck, SlidersHorizontal,
  Plug, Mail, ShieldCheck, Network, TrendingUp, UserCog, Bug, Radar, Route, Sparkles, GitCompare, Building2, Atom, type LucideIcon
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/hooks/use-auth";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  exact?: boolean;
  roles?: string[];
}

const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard",            label: "Overview",     icon: LayoutDashboard, exact: true },
  { href: "/dashboard/executive",  label: "Executive",    icon: TrendingUp, roles: ["admin", "super_admin", "analyst"] },
  { href: "/dashboard/simulations", label: "Simulations",  icon: Atom,       roles: ["admin", "super_admin", "analyst"] },
  { href: "/dashboard/ciem",        label: "CIEM",         icon: UserCog,    roles: ["admin", "super_admin", "analyst"] },
  { href: "/dashboard/detections",  label: "Detections",   icon: Radar,      roles: ["admin", "super_admin", "analyst"] },
  { href: "/dashboard/vulns",       label: "Vulnerabilities", icon: Bug,     roles: ["admin", "super_admin", "analyst"] },
  { href: "/dashboard/findings",        label: "Findings",        icon: AlertTriangle },
  { href: "/dashboard/security-graph", label: "Security Graph",   icon: Network, roles: ["admin", "super_admin", "analyst"] },
  { href: "/dashboard/attack-paths", label: "Attack Paths", icon: Route, roles: ["admin", "super_admin", "analyst"] },
  { href: "/dashboard/drift", label: "Drift", icon: GitCompare, roles: ["admin", "super_admin", "analyst"] },
  { href: "/dashboard/portfolio", label: "Portfolio", icon: Building2, roles: ["admin", "super_admin"] },
  { href: "/dashboard/accounts",        label: "AWS Accounts",     icon: CloudCog },
  { href: "/dashboard/compliance",      label: "Compliance",       icon: CheckSquare },
  { href: "/dashboard/team",       label: "Team",         icon: Users2 },
  { href: "/dashboard/audit",       label: "Audit Log",    icon: ClipboardList },
  { href: "/dashboard/suppression", label: "Suppression",  icon: ShieldOff },
  { href: "/dashboard/reports",     label: "Reports",      icon: BarChart3 },
  { href: "/dashboard/settings",    label: "Settings",     icon: Settings },
  { href: "/dashboard/settings/api-keys", label: "API Keys",  icon: KeyRound,         roles: ["admin", "super_admin"] },
  { href: "/dashboard/settings/webhooks", label: "Webhooks",  icon: Webhook,           roles: ["admin", "super_admin"] },
  { href: "/dashboard/remediation",       label: "Remediation", icon: ClipboardCheck },
  { href: "/dashboard/settings/workspace",     label: "Workspace",         icon: SlidersHorizontal, roles: ["admin", "super_admin"] },
  { href: "/dashboard/settings/integrations", label: "Integrations",      icon: Plug,              roles: ["admin", "super_admin"] },
  { href: "/dashboard/settings/email",        label: "Email",             icon: Mail },
  { href: "/dashboard/settings/prompts",     label: "AI Prompts",        icon: Sparkles,          roles: ["admin", "super_admin"] },
  { href: "/dashboard/settings/security",     label: "Security",          icon: ShieldCheck },
  { href: "/dashboard/settings/reports",      label: "Scheduled Reports", icon: BarChart3,          roles: ["admin", "super_admin"] },
];

export function SidebarNav() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const visibleItems = NAV_ITEMS.filter(item =>
    !item.roles || !user?.role || item.roles.includes(user.role)
  );

  return (
    <aside className="flex w-60 flex-col bg-slate-900 border-r border-slate-800">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 py-4 border-b border-slate-800">
        <Shield className="h-5 w-5 text-blue-400" />
        <span className="font-semibold text-sm text-white">Cloud Posture</span>
      </div>

      {/* Nav items */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {visibleItems.map((item) => {
          const isActive = item.exact ? pathname === item.href : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href as any}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-blue-600/20 text-blue-400 font-medium"
                  : "text-slate-400 hover:text-white hover:bg-slate-800"
              )}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* User footer */}
      <div className="border-t border-slate-800 px-3 py-3">
        {user && (
          <div className="mb-2 px-3 py-1.5">
            <p className="text-xs font-medium text-white truncate">{user.full_name}</p>
            <p className="text-xs text-slate-500 truncate">{user.email}</p>
          </div>
        )}
        <button
          onClick={logout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
