"use client";

import { useState, useEffect, useCallback } from "react";
import { useFocusShield } from "./focus-shield";
import { cn } from "@/lib/utils";

interface CalmModeToggleProps {
  className?: string;
  showTimer?: boolean;
  durationMinutes?: number;
}

const DEFAULT_DURATION = 25;

export function CalmModeToggle({ className, showTimer = true, durationMinutes = DEFAULT_DURATION }: CalmModeToggleProps) {
  const { isCalmMode, toggleCalmMode, calmModeTimeRemaining } = useFocusShield();
  const [localTimeRemaining, setLocalTimeRemaining] = useState<number | null>(null);

  useEffect(() => {
    if (isCalmMode && calmModeTimeRemaining !== null) {
      setLocalTimeRemaining(calmModeTimeRemaining);
    } else {
      setLocalTimeRemaining(null);
    }
  }, [isCalmMode, calmModeTimeRemaining]);

  const formatTime = useCallback((ms: number | null) => {
    if (ms === null) return `${durationMinutes}:00`;
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, "0")}`;
  }, [durationMinutes]);

  return (
    <button
      onClick={toggleCalmMode}
      className={cn(
        "inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm font-medium transition-all",
        isCalmMode ? "bg-green-500/20 text-green-400 border-green-500/50" : "hover:bg-muted",
        className
      )}
      aria-pressed={isCalmMode}
      title={isCalmMode ? "End Calm Mode" : "Start Calm Mode (Pomodoro)"}
    >
      <span className={cn("text-base", isCalmMode && "animate-pulse")}>
        {isCalmMode ? "🧘" : "🌙"}
      </span>
      <span>Calm Mode</span>
      {showTimer && localTimeRemaining !== null && (
        <span className="ml-1 font-mono text-xs text-muted-foreground">
          {formatTime(localTimeRemaining)}
        </span>
      )}
      {showTimer && !localTimeRemaining && (
        <span className="ml-1 font-mono text-xs text-muted-foreground">
          {durationMinutes}:00
        </span>
      )}
    </button>
  );
}

export function CalmModeIndicator({ className }: { className?: string }) {
  const { isCalmMode, calmModeTimeRemaining } = useFocusShield();

  if (!isCalmMode) return null;

  const formatTime = (ms: number | null) => {
    if (ms === null) return "";
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, "0")}`;
  };

  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 rounded-full bg-green-500/20 px-3 py-1 text-xs font-medium text-green-400",
        className
      )}
    >
      <span className="animate-pulse">🧘</span>
      <span>Calm Mode Active</span>
      <span className="font-mono">{formatTime(calmModeTimeRemaining)}</span>
    </div>
  );
}