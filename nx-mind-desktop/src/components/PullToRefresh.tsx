"use client";

import { useState, useRef, useCallback, ReactNode } from "react";

const PULL_THRESHOLD = 80;

interface PullToRefreshProps {
  children: ReactNode;
  onRefresh: () => Promise<void> | void;
  className?: string;
}

/**
 * Pull-to-refresh component using touch events
 * Shows loading indicator when pulled past threshold
 */
export function PullToRefresh({ children, onRefresh, className = "" }: PullToRefreshProps) {
  const [pullDistance, setPullDistance] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const startY = useRef(0);
  const isPulling = useRef(false);

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    startY.current = e.touches[0].clientY;
    isPulling.current = true;
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!isPulling.current) return;
    
    const currentY = e.touches[0].clientY;
    const diff = currentY - startY.current;
    
    // Only allow pulling down (positive diff) and if scrolled to top
    if (diff > 0) {
      setPullDistance(Math.min(diff, PULL_THRESHOLD * 1.5));
    }
  }, []);

  const handleTouchEnd = useCallback(async () => {
    isPulling.current = false;
    
    if (pullDistance >= PULL_THRESHOLD && !isRefreshing) {
      setIsRefreshing(true);
      setPullDistance(0);
      
      try {
        await onRefresh();
      } finally {
        setIsRefreshing(false);
      }
    } else {
      setPullDistance(0);
    }
  }, [pullDistance, isRefreshing, onRefresh]);

  return (
    <div
      className={`relative overflow-hidden ${className}`}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {/* Loading indicator */}
      <div
        className={`absolute top-0 left-0 right-0 flex items-center justify-center h-12 transition-transform duration-200 ease-out ${
          isRefreshing || pullDistance > 0 ? "translate-y-0" : "translate-y-[-100%]"
        }`}
        style={{
          transform: `translateY(${isRefreshing ? 0 : pullDistance * 0.5}px)`,
        }}
      >
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <span className="text-xs text-muted-foreground">Refreshing...</span>
        </div>
      </div>
      
      {/* Main content */}
      <div
        style={{
          transform: isRefreshing ? `translateY(${PULL_THRESHOLD}px)` : `translateY(${pullDistance * 0.3}px)`,
          transition: isRefreshing ? "none" : "transform 0.1s ease-out",
        }}
      >
        {children}
      </div>
    </div>
  );
}