"use client";

import React from "react";
import { cn } from "@/lib/utils";

export type SaveStatus = "saved" | "saving" | "unsaved" | "error";

interface SaveIndicatorProps {
  status: SaveStatus;
  lastSaved?: Date | null;
  showLabel?: boolean;
  className?: string;
}

export function SaveIndicator({
  status,
  lastSaved,
  showLabel = true,
  className,
}: SaveIndicatorProps) {
  const formatTime = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);

    if (seconds < 60) return "just now";
    if (minutes < 60) return `${minutes}m ago`;
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  return (
    <div className={cn("flex items-center gap-1.5 text-xs", className)}>
      <StatusIcon status={status} />
      {showLabel && (
        <StatusLabel status={status} lastSaved={lastSaved} formatTime={formatTime} />
      )}
    </div>
  );
}

function StatusIcon({ status }: { status: SaveStatus }) {
  switch (status) {
    case "saved":
      return (
        <svg
          className="w-3.5 h-3.5 text-green-400 animate-scale-in"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M5 13l4 4L19 7"
          />
        </svg>
      );
    case "saving":
      return (
        <svg
          className="w-3.5 h-3.5 text-cyan-400 animate-spin"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
          />
        </svg>
      );
    case "unsaved":
      return (
        <div className="w-2 h-2 rounded-full bg-yellow-400 animate-pulse" />
      );
    case "error":
      return (
        <svg
          className="w-3.5 h-3.5 text-destructive"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
      );
    default:
      return null;
  }
}

function StatusLabel({
  status,
  lastSaved,
  formatTime,
}: {
  status: SaveStatus;
  lastSaved?: Date | null;
  formatTime: (d: Date) => string;
}) {
  const labelClasses = {
    saved: "text-green-400/80",
    saving: "text-cyan-400",
    unsaved: "text-yellow-400/80",
    error: "text-destructive",
  };

  switch (status) {
    case "saved":
      return (
        <span className={cn("animate-fade-in", labelClasses.saved)}>
          {lastSaved ? formatTime(lastSaved) : "Saved"}
        </span>
      );
    case "saving":
      return <span className={labelClasses.saving}>Saving...</span>;
    case "unsaved":
      return <span className={labelClasses.unsaved}>Unsaved</span>;
    case "error":
      return <span className={labelClasses.error}>Save failed</span>;
    default:
      return null;
  }
}

interface AutoSaveProps {
  isSaving: boolean;
  lastSaved?: Date | null;
  error?: string | null;
  className?: string;
}

export function AutoSaveIndicator({
  isSaving,
  lastSaved,
  error,
  className,
}: AutoSaveProps) {
  const status: SaveStatus = error
    ? "error"
    : isSaving
    ? "saving"
    : lastSaved
    ? "saved"
    : "unsaved";

  return (
    <SaveIndicator
      status={status}
      lastSaved={lastSaved}
      className={className}
    />
  );
}

interface SavingDotsProps {
  className?: string;
}

export function SavingDots({ className }: SavingDotsProps) {
  return (
    <div className={cn("flex items-center gap-1", className)}>
      <span className="text-xs text-cyan-400">Saving</span>
      <div className="flex gap-0.5">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="w-1 h-1 rounded-full bg-cyan-400 animate-bounce"
            style={{
              animationDelay: `${i * 0.15}s`,
            }}
          />
        ))}
      </div>
    </div>
  );
}

export default SaveIndicator;