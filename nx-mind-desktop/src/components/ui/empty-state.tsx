"use client";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Brain,
  MessageSquare,
  Target,
  Search,
  Sparkles,
  Inbox,
  type LucideIcon,
} from "lucide-react";

export type EmptyStateVariant =
  | "default"
  | "no-memories"
  | "no-tasks"
  | "no-chats"
  | "no-results"
  | "no-agents";

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  variant?: EmptyStateVariant;
  className?: string;
  icon?: LucideIcon;
}

const variantConfigs: Record<
  EmptyStateVariant,
  {
    icon: LucideIcon;
    gradient: string;
    iconColor: string;
    glowClass: string;
  }
> = {
  default: {
    icon: Inbox,
    gradient: "from-violet-500/20 via-purple-500/10 to-transparent",
    iconColor: "text-purple-400",
    glowClass: "group-hover:shadow-[0_0_30px_rgba(139,92,246,0.4)]",
  },
  "no-memories": {
    icon: Brain,
    gradient: "from-blue-500/20 via-cyan-500/10 to-transparent",
    iconColor: "text-blue-400",
    glowClass: "group-hover:shadow-[0_0_30px_rgba(59,130,246,0.4)]",
  },
  "no-tasks": {
    icon: Target,
    gradient: "from-orange-500/20 via-amber-500/10 to-transparent",
    iconColor: "text-orange-400",
    glowClass: "group-hover:shadow-[0_0_30px_rgba(249,115,22,0.4)]",
  },
  "no-chats": {
    icon: MessageSquare,
    gradient: "from-green-500/20 via-emerald-500/10 to-transparent",
    iconColor: "text-green-400",
    glowClass: "group-hover:shadow-[0_0_30px_rgba(34,197,94,0.4)]",
  },
  "no-results": {
    icon: Search,
    gradient: "from-cyan-500/20 via-sky-500/10 to-transparent",
    iconColor: "text-cyan-400",
    glowClass: "group-hover:shadow-[0_0_30px_rgba(34,211,238,0.4)]",
  },
  "no-agents": {
    icon: Sparkles,
    gradient: "from-pink-500/20 via-rose-500/10 to-transparent",
    iconColor: "text-pink-400",
    glowClass: "group-hover:shadow-[0_0_30px_rgba(244,63,94,0.4)]",
  },
};

export function EmptyState({
  title,
  description,
  action,
  variant = "default",
  className,
  icon,
}: EmptyStateProps) {
  const config = variantConfigs[variant];
  const IconComponent = icon || config.icon;

  return (
    <div
      className={cn(
        "group relative flex flex-col items-center justify-center p-8 sm:p-12",
        className
      )}
    >
      {/* Ambient background glow */}
      <div
        className={cn(
          "absolute inset-0 bg-gradient-to-br opacity-0 group-hover:opacity-100 transition-opacity duration-500",
          config.gradient
        )}
        aria-hidden="true"
      />

      {/* Glass card container */}
      <div
        className={cn(
          "relative glass-card rounded-2xl p-8 sm:p-10 text-center",
          "transition-all duration-300 ease-out",
          "group-hover:scale-[1.02] group-hover:border-white/10",
          config.glowClass
        )}
      >
        {/* Icon container with gradient background */}
        <div
          className={cn(
            "relative mx-auto mb-6 w-20 h-20 sm:w-24 sm:h-24",
            "rounded-2xl",
            "bg-gradient-to-br from-white/5 to-white/0",
            "border border-white/10",
            "flex items-center justify-center",
            "transition-all duration-300 ease-out",
            "group-hover:scale-110 group-hover:border-white/20",
            "[&_*]:transition-all [&_*]:duration-300 [&_*]:ease-out"
          )}
          style={{
            boxShadow: `0 0 40px -10px currentColor`,
          }}
        >
          {/* Animated ring effect */}
          <div
            className={cn(
              "absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100",
              "bg-gradient-conic from-current via-transparent to-transparent",
              "blur-xl"
            )}
            style={{
              background: `conic-gradient(from 0deg, currentColor, transparent 60%, currentColor)`,
              mask: "radial-gradient(circle, black 30%, transparent 70%)",
              WebkitMask: "radial-gradient(circle, black 30%, transparent 70%)",
            }}
          />

          {/* Icon */}
          <IconComponent
            className={cn(
              "w-10 h-10 sm:w-12 sm:h-12",
              config.iconColor,
              "transition-transform duration-300 group-hover:scale-110",
              "[&_path]:transition-all [&_path]:duration-300 [&_path]:ease-out"
            )}
            strokeWidth={1.5}
          />

          {/* Floating particles effect */}
          <div className="absolute -inset-4 overflow-hidden rounded-2xl pointer-events-none">
            {[...Array(3)].map((_, i) => (
              <div
                key={i}
                className={cn(
                  "absolute w-1 h-1 rounded-full",
                  "bg-current opacity-0",
                  "animate-float",
                  config.iconColor
                )}
                style={{
                  left: `${30 + i * 20}%`,
                  top: `${40 + (i % 2) * 30}%`,
                  animationDelay: `${i * 0.3}s`,
                  animationDuration: `${2 + i * 0.5}s`,
                }}
              />
            ))}
          </div>
        </div>

        {/* Title */}
        <h3
          className={cn(
            "text-xl sm:text-2xl font-semibold",
            "bg-gradient-to-b from-white to-white/60",
            "bg-clip-text text-transparent",
            "mb-2 sm:mb-3",
            "transition-transform duration-300 group-hover:translate-y-[-2px]"
          )}
        >
          {title}
        </h3>

        {/* Description */}
        {description && (
          <p
            className={cn(
              "text-sm sm:text-base text-muted-foreground",
              "max-w-sm mx-auto",
              "leading-relaxed",
              "transition-all duration-300 group-hover:text-foreground/80"
            )}
          >
            {description}
          </p>
        )}

        {/* Action button */}
        {action && (
          <div className="mt-6 sm:mt-8">
            <Button
              onClick={action.onClick}
              className={cn(
                "relative overflow-hidden",
                "bg-gradient-to-r from-primary/90 to-primary",
                "hover:from-primary hover:to-primary/90",
                "text-primary-foreground",
                "font-medium",
                "px-6 py-2.5",
                "rounded-lg",
                "transition-all duration-300",
                "hover:scale-105 hover:shadow-lg hover:shadow-primary/25",
                "active:scale-[0.98]",
                "before:absolute before:inset-0 before:bg-gradient-to-r",
                "before:from-white/10 before:to-transparent",
                "before:opacity-0 hover:before:opacity-100",
                "before:transition-opacity before:duration-300"
              )}
            >
              <span className="relative z-10 flex items-center gap-2">
                {action.label}
              </span>
            </Button>
          </div>
        )}
      </div>

      {/* Decorative corner elements */}
      <div
        className={cn(
          "absolute top-0 left-0 w-16 h-16",
          "border-l-2 border-t-2 border-white/5 rounded-tl-2xl",
          "transition-all duration-300 group-hover:border-white/10"
        )}
      />
      <div
        className={cn(
          "absolute bottom-0 right-0 w-16 h-16",
          "border-r-2 border-b-2 border-white/5 rounded-br-2xl",
          "transition-all duration-300 group-hover:border-white/10"
        )}
      />
    </div>
  );
}

// Preset empty states for common use cases
export function NoMemoriesState({
  onCreate,
  hasSearchQuery,
}: {
  onCreate?: () => void;
  hasSearchQuery?: boolean;
}) {
  if (hasSearchQuery) {
    return (
      <EmptyState
        variant="no-results"
        title="No memories found"
        description="Try adjusting your search terms or filters to find what you're looking for."
        action={
          onCreate
            ? { label: "Clear Search", onClick: onCreate }
            : undefined
        }
      />
    );
  }

  return (
    <EmptyState
      variant="no-memories"
      title="No memories yet"
      description="Start building your memory store by creating your first memory. Memories help preserve context across sessions."
      action={
        onCreate ? { label: "Create First Memory", onClick: onCreate } : undefined
      }
    />
  );
}

export function NoTasksState({
  onCreate,
}: {
  onCreate?: () => void;
}) {
  return (
    <EmptyState
      variant="no-tasks"
      title="All caught up!"
      description="No tasks in queue. Create a new task to get started with orchestration."
      action={
        onCreate ? { label: "Create Task", onClick: onCreate } : undefined
      }
    />
  );
}

export function NoChatsState({
  onCreate,
}: {
  onCreate?: () => void;
}) {
  return (
    <EmptyState
      variant="no-chats"
      title="Start a conversation"
      description="Begin a new chat with your AI assistant to explore ideas, debug code, or get help with tasks."
      action={
        onCreate ? { label: "New Chat", onClick: onCreate } : undefined
      }
    />
  );
}

export function NoAgentsState() {
  return (
    <EmptyState
      variant="no-agents"
      title="No agents available"
      description="Configure agents in settings to enable the orchestration system."
    />
  );
}

export function NoSearchResultsState({
  searchQuery,
  onClear,
}: {
  searchQuery: string;
  onClear?: () => void;
}) {
  return (
    <EmptyState
      variant="no-results"
      title="No results found"
      description={`No matches found for "${searchQuery}". Try different keywords or check your filters.`}
      action={
        onClear ? { label: "Clear Search", onClick: onClear } : undefined
      }
    />
  );
}

export function NoActivitiesState({
  onRefresh,
}: {
  onRefresh?: () => void;
}) {
  return (
    <EmptyState
      variant="default"
      title="No recent activity"
      description="Activity will appear here as agents complete tasks and processes run."
      action={
        onRefresh ? { label: "Refresh", onClick: onRefresh } : undefined
      }
    />
  );
}
