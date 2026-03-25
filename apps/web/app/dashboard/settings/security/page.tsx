"use client";

import { useState } from "react";
import { Shield, ShieldCheck, Copy, Eye, EyeOff } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { useTotpStatus, setupTotp, verifyTotp, disableTotp } from "@/lib/hooks/use-totp";
import type { TotpSetupResponse } from "@/lib/types";

export default function SecurityPage() {
  const { status, isLoading, mutate } = useTotpStatus();
  const [step, setStep] = useState<"idle" | "setup" | "verify" | "disable">("idle");
  const [setupData, setSetupData] = useState<TotpSetupResponse | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showBackupCodes, setShowBackupCodes] = useState(false);
  const [copiedSecret, setCopiedSecret] = useState(false);

  const handleSetup = async () => {
    setError("");
    try {
      const data = await setupTotp();
      setSetupData(data);
      setStep("setup");
    } catch {
      setError("Failed to initialize 2FA setup. Please try again.");
    }
  };

  const handleVerify = async () => {
    setError("");
    try {
      await verifyTotp(code);
      setSuccess("Two-factor authentication is now active!");
      setStep("idle");
      setCode("");
      await mutate();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Verification failed.");
    }
  };

  const handleDisable = async () => {
    setError("");
    try {
      await disableTotp(code);
      setSuccess("Two-factor authentication has been disabled.");
      setStep("idle");
      setCode("");
      await mutate();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Disable failed. Check your code.");
    }
  };

  const copySecret = () => {
    if (setupData) {
      navigator.clipboard.writeText(setupData.secret);
      setCopiedSecret(true);
      setTimeout(() => setCopiedSecret(false), 2000);
    }
  };

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="h-8 w-48 bg-slate-100 animate-pulse rounded" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900">Security Settings</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Manage two-factor authentication and account security.
        </p>
      </div>

      {/* Success alert */}
      {success && (
        <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
          {success}
        </div>
      )}

      {/* Error alert */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* 2FA Status Card */}
      <div className="rounded-xl border border-slate-200 bg-white">
        {/* Card Header */}
        <div className="px-6 py-4 border-b border-slate-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {status?.enabled ? (
                <ShieldCheck className="h-5 w-5 text-green-500" />
              ) : (
                <Shield className="h-5 w-5 text-slate-400" />
              )}
              <h2 className="text-base font-semibold text-slate-900">
                Two-Factor Authentication
              </h2>
            </div>
            <span
              className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border ${
                status?.enabled
                  ? "bg-green-100 text-green-700 border-green-200"
                  : "bg-slate-100 text-slate-500 border-slate-200"
              }`}
            >
              {status?.enabled ? "Enabled" : "Disabled"}
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Add an extra layer of security using an authenticator app like Google
            Authenticator or Authy.
          </p>
        </div>

        {/* Card Content */}
        <div className="px-6 py-4 space-y-4">
          {/* Idle — not enabled */}
          {step === "idle" && !status?.enabled && (
            <button
              onClick={handleSetup}
              className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              <Shield className="h-4 w-4" />
              Enable Two-Factor Authentication
            </button>
          )}

          {/* Idle — enabled */}
          {step === "idle" && status?.enabled && (
            <button
              onClick={() => {
                setStep("disable");
                setError("");
              }}
              className="inline-flex items-center gap-2 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              Disable Two-Factor Authentication
            </button>
          )}

          {/* Setup step — show secret + verify */}
          {step === "setup" && setupData && (
            <div className="space-y-4">
              <div className="rounded-lg border border-slate-200 p-4 bg-slate-50 space-y-3">
                <p className="text-sm font-medium text-slate-700">
                  1. Scan this QR code with your authenticator app, or enter the
                  secret manually:
                </p>
                <div className="flex flex-col items-center gap-3 p-4 bg-white border rounded-lg w-fit">
                  <QRCodeSVG value={setupData.otpauth_uri} size={180} level="M" />
                  <p className="text-xs text-muted-foreground text-center">
                    Scan with Google Authenticator or Authy
                  </p>
                </div>
                <div className="flex items-center gap-2 p-3 bg-white border border-slate-200 rounded font-mono text-xs break-all text-slate-800">
                  <span className="flex-1">{setupData.secret}</span>
                  <button
                    onClick={copySecret}
                    className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700 bg-slate-100 hover:bg-slate-200 px-2 py-1 rounded transition-colors shrink-0"
                  >
                    <Copy className="h-3 w-3" />
                    {copiedSecret ? "Copied!" : "Copy"}
                  </button>
                </div>
              </div>

              <div className="space-y-2">
                <label className="block text-sm font-medium text-slate-700">
                  2. Enter the 6-digit code from your app to confirm:
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    inputMode="numeric"
                    placeholder="000000"
                    value={code}
                    onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                    maxLength={6}
                    className="w-36 rounded-lg border border-slate-200 px-3 py-2 text-center font-mono text-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    onClick={handleVerify}
                    disabled={code.length !== 6}
                    className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                  >
                    Verify & Activate
                  </button>
                  <button
                    onClick={() => {
                      setStep("idle");
                      setSetupData(null);
                      setCode("");
                    }}
                    className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>

              {/* Backup codes */}
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium text-slate-700">
                    Backup codes (save these securely!)
                  </p>
                  <button
                    onClick={() => setShowBackupCodes(!showBackupCodes)}
                    className="text-slate-400 hover:text-slate-600 transition-colors"
                    aria-label="Toggle backup codes visibility"
                  >
                    {showBackupCodes ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
                {showBackupCodes && (
                  <div className="grid grid-cols-2 gap-2 p-3 bg-slate-100 rounded font-mono text-sm text-slate-800">
                    {setupData.backup_codes.map((bc, i) => (
                      <span key={i} className="tracking-widest">
                        {bc}
                      </span>
                    ))}
                  </div>
                )}
                <p className="text-xs text-slate-500">
                  Each backup code can be used once if you lose access to your
                  authenticator app.
                </p>
              </div>
            </div>
          )}

          {/* Disable step */}
          {step === "disable" && (
            <div className="space-y-3">
              <p className="text-sm text-slate-500">
                Enter your current TOTP code to confirm disabling 2FA.
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  inputMode="numeric"
                  placeholder="000000"
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                  maxLength={6}
                  className="w-36 rounded-lg border border-slate-200 px-3 py-2 text-center font-mono text-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-red-500"
                />
                <button
                  onClick={handleDisable}
                  disabled={code.length !== 6}
                  className="bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                >
                  Confirm Disable
                </button>
                <button
                  onClick={() => {
                    setStep("idle");
                    setCode("");
                    setError("");
                  }}
                  className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
