"use client";

import { useEffect, useState } from "react";

interface LoadingBarProps {
  progress?: number;
  isLoading: boolean;
  message?: string;
}

export function LoadingBar({ progress, isLoading, message }: LoadingBarProps) {
  const [displayProgress, setDisplayProgress] = useState(0);

  useEffect(() => {
    if (isLoading && progress !== undefined) {
      setDisplayProgress(progress);
    } else if (isLoading) {
      const interval = setInterval(() => {
        setDisplayProgress((prev) => {
          if (prev >= 90) return prev;
          return prev + Math.random() * 15;
        });
      }, 200);
      return () => clearInterval(interval);
    } else {
      setDisplayProgress(100);
      const timeout = setTimeout(() => setDisplayProgress(0), 300);
      return () => clearTimeout(timeout);
    }
  }, [isLoading, progress]);

  if (!isLoading && displayProgress === 0) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-50 h-1 bg-background/80 backdrop-blur-sm">
      <div
        className="h-full bg-gradient-to-r from-primary via-secondary to-primary bg-[length:200%_100%] animate-[loading_1.5s_ease-in-out_infinite]"
        style={{
          width: `${displayProgress}%`,
          transition: "width 0.3s ease-out",
        }}
      />
      {message && (
        <div className="absolute top-2 left-1/2 -translate-x-1/2 text-xs text-muted-foreground animate-pulse">
          {message}
        </div>
      )}
      <style jsx>{`
        @keyframes loading {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
    </div>
  );
}

export function MiniLoadingIndicator({ size = 16 }: { size?: number }) {
  return (
    <div
      className="animate-pulse"
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: "linear-gradient(90deg, hsl(var(--primary)), hsl(var(--secondary)))",
        backgroundSize: "200% 100%",
        animation: "loading 1s ease-in-out infinite",
      }}
    />
  );
}