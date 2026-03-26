"use client";

import React from "react";
import { AlertTriangle } from "lucide-react";

interface PageWrapperProps {
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  isLoading?: boolean;
  error?: Error | null;
  onRetry?: () => void;
  children: React.ReactNode;
}

function SkeletonHeader() {
  return (
    <div className="mb-8 space-y-3">
      <div className="h-8 w-64 rounded-lg bg-slate-800 animate-pulse" />
      <div className="h-4 w-96 rounded-md bg-slate-800/60 animate-pulse" />
    </div>
  );
}

function SkeletonCards() {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="h-28 rounded-xl bg-slate-800 animate-pulse"
          style={{ animationDelay: `${i * 150}ms` }}
        />
      ))}
    </div>
  );
}

function LoadingState() {
  return (
    <div className="min-h-[60vh] p-6">
      <SkeletonHeader />
      <SkeletonCards />
    </div>
  );
}

function ErrorState({
  error,
  onRetry,
}: {
  error: Error;
  onRetry?: () => void;
}) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center p-6">
      <div className="w-full max-w-lg rounded-xl border border-red-500/30 bg-red-950/20 p-8 text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-500/10">
          <AlertTriangle className="h-6 w-6 text-red-400" />
        </div>
        <h3 className="mb-2 text-lg font-semibold text-red-300">
          Something went wrong
        </h3>
        <p className="mb-6 text-sm text-red-400/80">
          {error.message || "An unexpected error occurred."}
        </p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="inline-flex items-center gap-2 rounded-lg bg-red-500/20 px-5 py-2.5 text-sm font-medium text-red-300 transition-colors hover:bg-red-500/30 focus:outline-none focus:ring-2 focus:ring-red-500/40"
          >
            Retry
          </button>
        )}
      </div>
    </div>
  );
}

export function PageWrapper({
  title,
  subtitle,
  icon,
  isLoading = false,
  error = null,
  onRetry,
  children,
}: PageWrapperProps) {
  if (isLoading) {
    return <LoadingState />;
  }

  if (error) {
    return <ErrorState error={error} onRetry={onRetry} />;
  }

  return (
    <div className="min-h-screen bg-slate-950 p-6">
      <header className="mb-8">
        <div className="flex items-center gap-3">
          {icon && (
            <span className="text-slate-400">{icon}</span>
          )}
          <h1 className="text-2xl font-bold tracking-tight text-white">
            {title}
          </h1>
        </div>
        {subtitle && (
          <p className="mt-1 text-sm text-slate-400">{subtitle}</p>
        )}
      </header>
      {children}
    </div>
  );
}
