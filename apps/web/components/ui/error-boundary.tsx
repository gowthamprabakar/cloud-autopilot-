"use client";

import React from "react";
import { AlertTriangle, ChevronDown, ChevronUp, RotateCcw } from "lucide-react";

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  showStack: boolean;
}

export class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null, showStack: false };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("ErrorBoundary:", error, info);
  }

  handleReload = () => {
    this.setState({ hasError: false, error: null, showStack: false });
  };

  toggleStack = () => {
    this.setState((prev) => ({ showStack: !prev.showStack }));
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const { error, showStack } = this.state;

      return (
        <div className="flex min-h-[40vh] items-center justify-center p-6">
          <div className="w-full max-w-lg rounded-xl border border-red-500/30 bg-slate-900 p-8">
            <div className="mb-4 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-500/10">
                <AlertTriangle className="h-5 w-5 text-red-400" />
              </div>
              <h3 className="text-lg font-semibold text-red-300">
                Something went wrong
              </h3>
            </div>

            <p className="mb-4 text-sm text-slate-400">
              {error?.message || "An unexpected error occurred."}
            </p>

            <div className="flex items-center gap-3">
              <button
                onClick={this.handleReload}
                className="inline-flex items-center gap-2 rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-slate-200 transition-colors hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-500/40"
              >
                <RotateCcw className="h-4 w-4" />
                Reload
              </button>

              {error?.stack && (
                <button
                  onClick={this.toggleStack}
                  className="inline-flex items-center gap-1 text-xs text-slate-500 transition-colors hover:text-slate-300"
                >
                  {showStack ? (
                    <>
                      Hide details <ChevronUp className="h-3 w-3" />
                    </>
                  ) : (
                    <>
                      Show details <ChevronDown className="h-3 w-3" />
                    </>
                  )}
                </button>
              )}
            </div>

            {showStack && error?.stack && (
              <pre className="mt-4 max-h-48 overflow-auto rounded-lg bg-slate-950 p-4 text-xs text-slate-500">
                {error.stack}
              </pre>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
