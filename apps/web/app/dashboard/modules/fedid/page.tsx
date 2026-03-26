"use client";

import { useState } from "react";
import {
  Fingerprint, ShieldAlert, Globe, Clock, KeyRound,
  CheckCircle2, XCircle, AlertTriangle, Link2, Users,
  Lock, RefreshCw, Building2,
} from "lucide-react";
import { useModuleEndpoint } from "@/lib/hooks/use-module-data";
import { cn } from "@/lib/utils";

// ── Types ────────────────────────────────────────────────────────────────────

interface SAMLProvider {
  id: string;
  provider_name: string;
  entity_id: string;
  cert_age_days: number;
  rotation_status: "current" | "expiring" | "expired";
  apt29_indicators: number;
  last_audit: string;
}

interface OIDCCheck {
  check: string;
  status: "pass" | "fail";
}

interface OIDCProvider {
  id: string;
  provider_name: string;
  issuer: string;
  checks: OIDCCheck[];
}

interface CrossCloudIdentity {
  id: string;
  identity: string;
  aws_role: string | null;
  azure_principal: string | null;
  gcp_sa: string | null;
  status: "active" | "orphaned" | "stale";
  last_activity: string;
}

interface RevocationProvider {
  id: string;
  provider_name: string;
  sla_seconds: number;
  target_seconds: number;
  meets_sla: boolean;
  mass_revocation: boolean;
  last_tested: string;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

const ROTATION_BADGE: Record<string, string> = {
  current:  "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
  expiring: "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20",
  expired:  "bg-red-500/10 text-red-400 border border-red-500/20",
};

const STATUS_BADGE: Record<string, string> = {
  active:   "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
  orphaned: "bg-red-500/10 text-red-400 border border-red-500/20",
  stale:    "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20",
};

// ── Summary Card ─────────────────────────────────────────────────────────────

function SummaryCard({
  label, value, icon: Icon, accent = "text-blue-400", sub,
}: {
  label: string; value: string | number; icon: React.ElementType;
  accent?: string; sub?: string;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5 flex flex-col gap-1">
      <div className="flex items-center gap-2 text-xs text-slate-500 uppercase tracking-wider">
        <Icon className={cn("h-4 w-4", accent)} />
        {label}
      </div>
      <p className="text-2xl font-semibold text-white">{value}</p>
      {sub && <p className="text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

// ── Tab Button ───────────────────────────────────────────────────────────────

type Tab = "golden-saml" | "oidc" | "cross-cloud" | "revocation";

function TabButton({ active, label, onClick }: {
  active: boolean; label: string; onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "px-4 py-2 text-sm font-medium rounded-lg transition-colors",
        active
          ? "bg-blue-600/20 text-blue-400"
          : "text-slate-400 hover:text-white hover:bg-slate-800",
      )}
    >
      {label}
    </button>
  );
}

// ── Golden SAML Tab ──────────────────────────────────────────────────────────

function GoldenSAMLTab({ providers }: { providers: SAMLProvider[] }) {
  if (providers.length === 0) {
    return (
      <div className="text-center py-16 text-slate-500">
        <ShieldAlert className="h-8 w-8 mx-auto mb-3 opacity-40" />
        <p>No SAML providers configured.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-slate-500 uppercase tracking-wider border-b border-slate-800">
            <th className="py-3 px-4">Provider</th>
            <th className="py-3 px-4">Entity ID</th>
            <th className="py-3 px-4">Cert Age (days)</th>
            <th className="py-3 px-4">Rotation Status</th>
            <th className="py-3 px-4">APT29 Indicators</th>
            <th className="py-3 px-4">Last Audit</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60">
          {providers.map((p) => (
            <tr key={p.id} className="hover:bg-slate-800/40 transition-colors">
              <td className="py-3 px-4">
                <div className="flex items-center gap-2">
                  <KeyRound className="h-4 w-4 text-orange-400" />
                  <span className="text-white font-medium">{p.provider_name}</span>
                </div>
              </td>
              <td className="py-3 px-4 text-slate-400 font-mono text-xs max-w-[200px] truncate">{p.entity_id}</td>
              <td className="py-3 px-4">
                <span className={cn("text-sm font-semibold", p.cert_age_days > 365 ? "text-red-400" : p.cert_age_days > 180 ? "text-yellow-400" : "text-emerald-400")}>
                  {p.cert_age_days}
                </span>
              </td>
              <td className="py-3 px-4">
                <span className={cn("text-xs px-2 py-0.5 rounded-full capitalize", ROTATION_BADGE[p.rotation_status])}>
                  {p.rotation_status}
                </span>
              </td>
              <td className="py-3 px-4">
                {p.apt29_indicators > 0 ? (
                  <span className="flex items-center gap-1 text-xs text-red-400">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    {p.apt29_indicators} detected
                  </span>
                ) : (
                  <span className="text-xs text-emerald-400">Clean</span>
                )}
              </td>
              <td className="py-3 px-4 text-slate-400 text-xs">{p.last_audit || "\u2014"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── OIDC Validation Tab ──────────────────────────────────────────────────────

const OIDC_CHECKS = ["audience", "issuer", "lifetime", "PKCE", "binding", "thumbprint"];

function OIDCValidationTab({ providers }: { providers: OIDCProvider[] }) {
  if (providers.length === 0) {
    return (
      <div className="text-center py-16 text-slate-500">
        <Lock className="h-8 w-8 mx-auto mb-3 opacity-40" />
        <p>No OIDC providers configured.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-slate-500 uppercase tracking-wider border-b border-slate-800">
            <th className="py-3 px-4">Provider</th>
            <th className="py-3 px-4">Issuer</th>
            {OIDC_CHECKS.map((c) => (
              <th key={c} className="py-3 px-4 text-center">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60">
          {providers.map((p) => {
            const checkMap = new Map(p.checks.map((c) => [c.check, c.status]));
            return (
              <tr key={p.id} className="hover:bg-slate-800/40 transition-colors">
                <td className="py-3 px-4 text-white font-medium">{p.provider_name}</td>
                <td className="py-3 px-4 text-slate-400 font-mono text-xs max-w-[180px] truncate">{p.issuer}</td>
                {OIDC_CHECKS.map((c) => {
                  const status = checkMap.get(c);
                  return (
                    <td key={c} className="py-3 px-4 text-center">
                      {status === "pass" ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-400 mx-auto" />
                      ) : status === "fail" ? (
                        <XCircle className="h-4 w-4 text-red-400 mx-auto" />
                      ) : (
                        <span className="text-slate-600">\u2014</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Cross-Cloud Tab ──────────────────────────────────────────────────────────

function CrossCloudTab({ identities }: { identities: CrossCloudIdentity[] }) {
  if (identities.length === 0) {
    return (
      <div className="text-center py-16 text-slate-500">
        <Globe className="h-8 w-8 mx-auto mb-3 opacity-40" />
        <p>No cross-cloud identity correlations found.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-slate-500 uppercase tracking-wider border-b border-slate-800">
            <th className="py-3 px-4">Identity</th>
            <th className="py-3 px-4">AWS IAM Role</th>
            <th className="py-3 px-4">Azure AD Principal</th>
            <th className="py-3 px-4">GCP IAM SA</th>
            <th className="py-3 px-4">Status</th>
            <th className="py-3 px-4">Last Activity</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60">
          {identities.map((id) => (
            <tr key={id.id} className="hover:bg-slate-800/40 transition-colors">
              <td className="py-3 px-4">
                <div className="flex items-center gap-2">
                  <Users className="h-4 w-4 text-blue-400" />
                  <span className="text-white font-medium">{id.identity}</span>
                </div>
              </td>
              <td className="py-3 px-4 text-slate-400 font-mono text-xs">{id.aws_role || "\u2014"}</td>
              <td className="py-3 px-4 text-slate-400 font-mono text-xs">{id.azure_principal || "\u2014"}</td>
              <td className="py-3 px-4 text-slate-400 font-mono text-xs">{id.gcp_sa || "\u2014"}</td>
              <td className="py-3 px-4">
                <span className={cn("text-xs px-2 py-0.5 rounded-full capitalize", STATUS_BADGE[id.status])}>
                  {id.status}
                </span>
              </td>
              <td className="py-3 px-4 text-slate-400 text-xs">{id.last_activity || "\u2014"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Token Revocation Tab ─────────────────────────────────────────────────────

function TokenRevocationTab({ providers }: { providers: RevocationProvider[] }) {
  if (providers.length === 0) {
    return (
      <div className="text-center py-16 text-slate-500">
        <RefreshCw className="h-8 w-8 mx-auto mb-3 opacity-40" />
        <p>No revocation provider data.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-slate-500 uppercase tracking-wider border-b border-slate-800">
            <th className="py-3 px-4">Provider</th>
            <th className="py-3 px-4">Current SLA</th>
            <th className="py-3 px-4">Target</th>
            <th className="py-3 px-4">SLA Met</th>
            <th className="py-3 px-4">Mass Revocation</th>
            <th className="py-3 px-4">Last Tested</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60">
          {providers.map((p) => {
            const slaMin = Math.round(p.sla_seconds / 60);
            const targetMin = Math.round(p.target_seconds / 60);
            return (
              <tr key={p.id} className="hover:bg-slate-800/40 transition-colors">
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2">
                    <Building2 className="h-4 w-4 text-blue-400" />
                    <span className="text-white font-medium">{p.provider_name}</span>
                  </div>
                </td>
                <td className="py-3 px-4">
                  <span className={cn("text-sm font-semibold", p.meets_sla ? "text-emerald-400" : "text-red-400")}>
                    {slaMin} min
                  </span>
                </td>
                <td className="py-3 px-4 text-slate-400 text-xs">{targetMin} min</td>
                <td className="py-3 px-4">
                  {p.meets_sla ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  ) : (
                    <XCircle className="h-4 w-4 text-red-400" />
                  )}
                </td>
                <td className="py-3 px-4">
                  {p.mass_revocation ? (
                    <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      <CheckCircle2 className="h-3 w-3" /> Capable
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/20">
                      <XCircle className="h-3 w-3" /> Unavailable
                    </span>
                  )}
                </td>
                <td className="py-3 px-4 text-slate-400 text-xs">{p.last_tested || "\u2014"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Loading Skeleton ─────────────────────────────────────────────────────────

function Skeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-xl border border-slate-800 bg-slate-900 p-5 h-24" />
        ))}
      </div>
      <div className="rounded-xl border border-slate-800 bg-slate-900 h-64" />
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function FederatedIdentityPage() {
  const [tab, setTab] = useState<Tab>("golden-saml");
  const { data: samlData, isLoading: samlLoading } = useModuleEndpoint("federated-id", "golden-saml");
  const { data: crossData, isLoading: crossLoading } = useModuleEndpoint("federated-id", "cross-cloud");
  const { data: oidcData, isLoading: oidcLoading } = useModuleEndpoint("federated-id", "oidc");
  const { data: revoData, isLoading: revoLoading } = useModuleEndpoint("federated-id", "token-revocation");

  const isLoading = samlLoading || crossLoading || oidcLoading || revoLoading;

  const samlProviders: SAMLProvider[] = samlData?.providers ?? [];
  const oidcProviders: OIDCProvider[] = oidcData?.providers ?? [];
  const crossIdentities: CrossCloudIdentity[] = crossData?.identities ?? [];
  const revoProviders: RevocationProvider[] = revoData?.providers ?? [];

  const totalIdps = samlProviders.length + oidcProviders.length;
  const trustRelations = crossIdentities.filter((i) => i.status === "active").length;
  const samlRisks = samlProviders.filter((p) => p.apt29_indicators > 0 || p.rotation_status === "expired").length;
  const avgSla = revoProviders.length > 0
    ? `${Math.round(revoProviders.reduce((sum, p) => sum + p.sla_seconds, 0) / revoProviders.length / 60)} min`
    : "\u2014";

  if (isLoading) {
    return (
      <div className="flex-1 overflow-auto p-6 lg:p-10 bg-slate-950">
        <div className="flex items-center gap-3 mb-8">
          <Fingerprint className="h-6 w-6 text-orange-400" />
          <h1 className="text-xl font-semibold text-white">Federated Identity</h1>
        </div>
        <Skeleton />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-auto p-6 lg:p-10 bg-slate-950">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <Fingerprint className="h-6 w-6 text-orange-400" />
        <div>
          <h1 className="text-xl font-semibold text-white">Federated Identity</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Cross-cloud identity security &mdash; Golden SAML, OIDC validation, trust correlation & token revocation
          </p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <SummaryCard label="Identity Providers" value={totalIdps} icon={Users} accent="text-blue-400" sub="SAML + OIDC providers" />
        <SummaryCard label="Trust Relationships" value={trustRelations} icon={Link2} accent="text-purple-400" sub="active cross-cloud trusts" />
        <SummaryCard label="SAML Risks" value={samlRisks} icon={ShieldAlert} accent="text-red-400" sub="expired certs or APT29 signals" />
        <SummaryCard label="Revocation SLA" value={avgSla} icon={Clock} accent="text-yellow-400" sub="avg across providers (5-min target)" />
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 mb-6">
        <TabButton active={tab === "golden-saml"} label="Golden SAML" onClick={() => setTab("golden-saml")} />
        <TabButton active={tab === "oidc"} label="OIDC Validation" onClick={() => setTab("oidc")} />
        <TabButton active={tab === "cross-cloud"} label="Cross-Cloud" onClick={() => setTab("cross-cloud")} />
        <TabButton active={tab === "revocation"} label="Token Revocation" onClick={() => setTab("revocation")} />
      </div>

      {/* Tab Content */}
      <div className="rounded-xl border border-slate-800 bg-slate-900">
        {tab === "golden-saml" && <GoldenSAMLTab providers={samlProviders} />}
        {tab === "oidc" && <OIDCValidationTab providers={oidcProviders} />}
        {tab === "cross-cloud" && <CrossCloudTab identities={crossIdentities} />}
        {tab === "revocation" && <TokenRevocationTab providers={revoProviders} />}
      </div>
    </div>
  );
}
