/** Centralized color tokens for OmniSec — single source of truth. */

export const AGENT_COLORS: Record<string, string> = {
  "ORCH-01": "#FF6B35", "SCOUT-01": "#00D4FF", "EXPLOIT-01": "#FF3366",
  "DEFEND-01": "#00FF88", "VALID-01": "#FFD700", "REPORT-01": "#9B59B6",
  "WIZ-CSPM": "#3498DB", "WIZ-CIEM": "#E67E22", "WIZ-CDR": "#E74C3C",
  "WIZ-DSPM": "#2ECC71", "WIZ-KSPM": "#326CE5", "WIZ-IaC": "#F39C12",
  "WIZ-UVM": "#E74C3C", "WIZ-AISPM": "#9B59B6", "WIZ-ASM": "#1ABC9C",
  "QUANT-01": "#8E44AD", "FAKE-01": "#D35400", "CHAIN-01": "#27AE60",
  "OT-01": "#95A5A6", "LLM-01": "#1ABC9C", "DEEP-XX": "#BDC3C7",
};

export const STATUS_COLORS = {
  standby: "#64748B", initializing: "#F59E0B", running: "#3B82F6",
  certified: "#22C55E", error: "#EF4444",
} as const;

export const MESSAGE_TYPE_COLORS = {
  info: "#3B82F6", solution: "#22C55E", alert: "#EF4444",
  spawn: "#A855F7", wiz: "#F97316",
} as const;

export const SEVERITY_COLORS = {
  critical: "#DC2626", high: "#EA580C", medium: "#D97706",
  low: "#65A30D", info: "#6B7280",
} as const;

export const DOMAIN_ACCENTS: Record<string, string> = {
  cspm: "#8B5CF6", cwpp: "#3B82F6", ciem: "#F59E0B", dspm: "#22C55E",
  kspm: "#326CE5", cdr: "#EF4444", iac: "#F97316", uvm: "#DC2626",
  ai_spm: "#A855F7", asm: "#14B8A6", quantum: "#8B5CF6", deepfake: "#D97706",
  supply_chain: "#22C55E", agentic_ai: "#F43F5E", ot_ics: "#6B7280",
  llmjacking: "#14B8A6", federated_id: "#F59E0B",
};
