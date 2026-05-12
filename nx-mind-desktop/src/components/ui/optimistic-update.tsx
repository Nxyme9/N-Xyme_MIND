"use client";

import React from "react";
import { useToast } from "./use-toast";

interface OptimisticUIProps {
  isPending: boolean;
  error: Error | null;
  children: React.ReactNode;
  fallback?: React.ReactNode;
  onError?: (error: Error) => void;
}

export function OptimisticUI({
  isPending,
  error,
  children,
  fallback,
  onError,
}: OptimisticUIProps) {
  const { toast } = useToast();

  React.useEffect(() => {
    if (error) {
      toast({
        title: "Something went wrong",
        description: error.message || "Failed to save changes",
        variant: "error",
        duration: 5000,
      });
      onError?.(error);
    }
  }, [error, toast, onError]);

  if (isPending) {
    return (
      <>{fallback || <OptimisticFallback />}</>
    );
  }

  if (error) {
    return (
      <>{fallback || <OptimisticError error={error} />}</>
    );
  }

  return <>{children}</>;
}

function OptimisticFallback() {
  return (
    <div className="animate-pulse-glow rounded-lg border border-primary/30 bg-primary/5 p-4">
      <div className="flex items-center gap-3">
        <div className="h-4 w-4 rounded-full bg-primary/50 animate-ping" />
        <span className="text-sm text-primary/70">Saving...</span>
      </div>
    </div>
  );
}

function OptimisticError({ error }: { error: Error }) {
  return (
    <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
      <div className="flex items-center gap-3">
        <svg
          className="h-4 w-4 text-destructive"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
        <span className="text-sm text-destructive">
          {error.message || "Failed to save"}
        </span>
      </div>
    </div>
  );
}

interface OptimisticButtonProps {
  isPending: boolean;
  children: React.ReactNode;
  className?: string;
  disabled?: boolean;
}

export function OptimisticButton({
  isPending,
  children,
  className = "",
  disabled,
}: OptimisticButtonProps) {
  return (
    <button
      className={`relative ${className}`}
      disabled={isPending || disabled}
      style={{
        opacity: isPending ? 0.8 : 1,
        transition: "opacity 200ms ease",
      }}
    >
      {isPending && (
        <span
          className="absolute inset-0 flex items-center justify-center"
          style={{
            background: "inherit",
            borderRadius: "inherit",
          }}
        >
          <svg
            className="animate-spin h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            style={{ color: "hsl(var(--primary))" }}
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        </span>
      )}
      {children}
    </button>
  );
}

export default OptimisticUI;