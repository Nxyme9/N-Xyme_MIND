"use client";

import { useCognitiveState, type CognitiveState } from "@/hooks/useCognitiveState";
import { cn } from "@/lib/utils";

const STATE_CONFIG: Record<CognitiveState, { label: string; icon: string; description: string }> = {
  surge: { label: "SURGE", icon: "⚡", description: "High bandwidth - cockpit-dense UI" },
  drift: { label: "DRIFT", icon: "🌊", description: "Normal attention - curated single-panel" },
  dawn: { label: "DAWN", icon: "🌅", description: "Low bandwidth - simple chunky UI" },
};

interface CognitiveStateToggleProps {
  className?: string;
  showLabels?: boolean;
  size?: "sm" | "md" | "lg";
}

export function CognitiveStateToggle({ className, showLabels = true, size = "md" }: CognitiveStateToggleProps) {
  const { cognitiveState, setCognitiveState, autoDetected } = useCognitiveState();

  const sizeClasses = {
    sm: "h-8 text-xs px-2 gap-1",
    md: "h-10 text-sm px-3 gap-2",
    lg: "h-12 text-base px-4 gap-3",
  };

  const iconSizes = { sm: "text-base", md: "text-lg", lg: "text-xl" };

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-lg border border-border bg-card p-1",
        sizeClasses[size],
        className
      )}
      role="group"
      aria-label="Cognitive state toggle"
    >
      {(Object.keys(STATE_CONFIG) as CognitiveState[]).map((state) => {
        const isActive = cognitiveState === state;
        const config = STATE_CONFIG[state];

        return (
          <button
            key={state}
            onClick={() => setCognitiveState(state, false)}
            className={cn(
              "flex items-center rounded-md px-2 py-1 font-medium transition-all duration-150",
              isActive
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground hover:bg-muted"
            )}
            aria-pressed={isActive}
            title={config.description}
          >
            <span className={iconSizes[size]}>{config.icon}</span>
            {showLabels && <span className="ml-1">{config.label}</span>}
          </button>
        );
      })}
      {autoDetected && (
        <span className="ml-2 text-xs text-muted-foreground" title="Auto-detected from orchestration">
          🤖
        </span>
      )}
    </div>
  );
}

export function CognitiveStateIndicator({ className }: { className?: string }) {
  const { cognitiveState } = useCognitiveState();
  const config = STATE_CONFIG[cognitiveState];

  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5 text-sm",
        className
      )}
    >
      <span>{config.icon}</span>
      <span className="font-medium">{config.label}</span>
      <span className="text-muted-foreground">- {config.description.split(" - ")[1]}</span>
    </div>
  );
}