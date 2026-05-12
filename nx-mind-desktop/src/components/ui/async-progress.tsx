"use client";

import React from "react";
import { cn } from "@/lib/utils";

interface ProgressBarProps {
  progress: number;
  label?: string;
  showPercentage?: boolean;
  size?: "sm" | "md" | "lg";
  variant?: "neon" | "gradient" | "solid";
  animated?: boolean;
  className?: string;
}

export function ProgressBar({
  progress,
  label,
  showPercentage = true,
  size = "md",
  variant = "neon",
  animated = true,
  className,
}: ProgressBarProps) {
  const clampedProgress = Math.min(100, Math.max(0, progress));

  const heights = {
    sm: "h-1",
    md: "h-2",
    lg: "h-3",
  };

  const baseClasses = "w-full rounded-full overflow-hidden";

  const variantClasses = {
    neon: "bg-gradient-to-r from-cyan-500/20 via-primary/30 to-cyan-500/20",
    gradient: "bg-gradient-to-r from-primary/20 via-secondary/30 to-primary/20",
    solid: "bg-muted",
  };

  return (
    <div className={cn("space-y-2", className)}>
      {(label || showPercentage) && (
        <div className="flex justify-between items-center text-sm">
          {label && (
            <span className="text-muted-foreground font-medium">
              {label}
            </span>
          )}
          {showPercentage && (
            <span
              className={cn(
                "font-mono tabular-nums transition-all duration-200",
                clampedProgress === 100
                  ? "text-green-400"
                  : clampedProgress > 50
                  ? "text-cyan-400"
                  : "text-primary"
              )}
            >
              {Math.round(clampedProgress)}%
            </span>
          )}
        </div>
      )}
      <div className={cn(baseClasses, heights[size], variantClasses[variant])}>
        <div
          className={cn(
            "h-full rounded-full transition-all duration-300 ease-out",
            variant === "neon" && [
              "bg-gradient-to-r from-cyan-400 via-primary to-cyan-400",
              "shadow-[0_0_10px_hsl(180_100%_50%/0.5),0_0_20px_hsl(280_100%_60%/0.3)]",
            ],
            variant === "gradient" && [
              "bg-gradient-to-r from-primary via-secondary to-primary",
            ],
            variant === "solid" && "bg-primary",
            animated && "animate-progress-stripes"
          )}
          style={{
            width: `${clampedProgress}%`,
          }}
        />
      </div>
      <style jsx>{`
        @keyframes progress-stripes {
          0% {
            background-position: 1rem 0;
          }
          100% {
            background-position: 0 0;
          }
        }
        .animate-progress-stripes {
          background-size: 1rem 1rem;
          animation: progress-stripes 1s linear infinite;
        }
      `}</style>
    </div>
  );
}

interface CircularProgressProps {
  progress: number;
  size?: number;
  strokeWidth?: number;
  label?: string;
  showPercentage?: boolean;
  className?: string;
}

export function CircularProgress({
  progress,
  size = 48,
  strokeWidth = 4,
  label,
  showPercentage = true,
  className,
}: CircularProgressProps) {
  const clampedProgress = Math.min(100, Math.max(0, progress));
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (clampedProgress / 100) * circumference;

  return (
    <div className={cn("relative inline-flex items-center justify-center", className)}>
      <svg width={size} height={size} className="transform -rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="hsl(var(--muted))"
          strokeWidth={strokeWidth}
          fill="none"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="url(#progress-gradient)"
          strokeWidth={strokeWidth}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-300 ease-out"
          style={{
            filter: "drop-shadow(0 0 6px hsl(180 100% 50% / 0.5))",
          }}
        />
        <defs>
          <linearGradient id="progress-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="hsl(180 100% 50%)" />
            <stop offset="50%" stopColor="hsl(280 100% 60%)" />
            <stop offset="100%" stopColor="hsl(180 100% 50%)" />
          </linearGradient>
        </defs>
      </svg>
      {showPercentage && (
        <span className="absolute text-xs font-mono font-medium text-foreground">
          {Math.round(clampedProgress)}
        </span>
      )}
      {label && (
        <span className="absolute -bottom-5 text-xs text-muted-foreground whitespace-nowrap">
          {label}
        </span>
      )}
    </div>
  );
}

interface MiniProgressProps {
  progress?: number;
  isIndeterminate?: boolean;
  size?: number;
  className?: string;
}

export function MiniProgress({
  progress,
  isIndeterminate = true,
  size = 16,
  className,
}: MiniProgressProps) {
  return (
    <div
      className={cn(
        "rounded-full overflow-hidden",
        className
      )}
      style={{
        width: size,
        height: size / 3,
        background: "hsl(var(--muted) / 0.3)",
      }}
    >
      <div
        className="h-full rounded-full bg-gradient-to-r from-cyan-400 via-primary to-cyan-400 animate-progress-stripes"
        style={{
          width: isIndeterminate ? "30%" : `${progress}%`,
          transition: isIndeterminate ? "none" : "width 200ms ease",
        }}
      />
    </div>
  );
}

export default ProgressBar;