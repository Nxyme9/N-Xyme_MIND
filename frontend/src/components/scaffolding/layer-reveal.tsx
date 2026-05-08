"use client";

import { useState, useEffect, type ReactNode } from "react";
import { cn } from "@/lib/utils";

interface LayerRevealProps {
  children: ReactNode;
  isVisible: boolean;
  layer: number;
  className?: string;
}

const ANIMATION_CONFIG = {
  enter: "var(--motion-enter)",
  exit: "var(--motion-exit)",
};

export function LayerReveal({ children, isVisible, layer, className }: LayerRevealProps) {
  const [isMounted, setIsMounted] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);

  useEffect(() => {
    if (isVisible) {
      setIsMounted(true);
      setIsAnimating(true);
      const timer = setTimeout(() => setIsAnimating(false), 250);
      return () => clearTimeout(timer);
    } else {
      setIsAnimating(true);
      const timer = setTimeout(() => setIsMounted(false), 350);
      return () => clearTimeout(timer);
    }
  }, [isVisible]);

  if (!isMounted) return null;

  return (
    <div
      className={cn(
        "transition-all overflow-hidden",
        isVisible ? "animate-page-enter" : "animate-page-exit",
        className
      )}
      style={{
        animationDuration: isVisible
          ? "250ms"
          : "350ms",
      }}
    >
      {children}
    </div>
  );
}

interface StaggerRevealProps {
  children: ReactNode;
  staggerIndex?: number;
  className?: string;
}

export function StaggerReveal({ children, staggerIndex = 0, className }: StaggerRevealProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), staggerIndex * 50);
    return () => clearTimeout(timer);
  }, [staggerIndex]);

  return (
    <div
      className={cn(
        "transition-all duration-300",
        isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4",
        className
      )}
    >
      {children}
    </div>
  );
}

interface AttentionAnchorProps {
  type: "ripple" | "progress" | "shimmer";
  isActive?: boolean;
  className?: string;
}

export function AttentionAnchor({ type, isActive = true, className }: AttentionAnchorProps) {
  if (!isActive) return null;

  switch (type) {
    case "ripple":
      return <div className={cn("animate-ripple", className)} />;
    case "progress":
      return <div className={cn("animate-progress-line h-0.5 bg-primary", className)} />;
    case "shimmer":
      return <div className={cn("animate-shimmer-sweep h-full", className)} />;
    default:
      return null;
  }
}

interface ProgressiveRevealProps {
  items: ReactNode[];
  maxVisible?: number;
  expandTrigger?: ReactNode;
  onExpand?: () => void;
  className?: string;
}

export function ProgressiveReveal({
  items,
  maxVisible = 3,
  expandTrigger,
  onExpand,
  className,
}: ProgressiveRevealProps) {
  const [expanded, setExpanded] = useState(false);
  const visibleItems = expanded ? items : items.slice(0, maxVisible);
  const hasMore = items.length > maxVisible;

  const handleExpand = () => {
    setExpanded(true);
    onExpand?.();
  };

  return (
    <div className={cn("space-y-2", className)}>
      {visibleItems.map((item, index) => (
        <StaggerReveal key={index} staggerIndex={index}>
          {item}
        </StaggerReveal>
      ))}
      {!expanded && hasMore && (
        <button
          onClick={handleExpand}
          className="text-sm text-muted-foreground hover:text-primary transition-colors"
        >
          {expandTrigger || `Show ${items.length - maxVisible} more...`}
        </button>
      )}
    </div>
  );
}