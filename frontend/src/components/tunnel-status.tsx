"use client";

import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";

interface TunnelStatusData {
  key?: {
    provider: string;
    in_use: boolean;
    current_key_index: number;
    total_keys: number;
  };
  model?: {
    current: string;
    fallback: string | null;
  };
  ip?: {
    current: string;
    rotating: boolean;
  };
  health?: {
    status: string;
    latency_ms: number;
  };
  fallback_mode?: boolean;
  error?: string;
}

interface TunnelStatusProps {
  className?: string;
  refreshInterval?: number;
}

export function TunnelStatus({ className, refreshInterval = 30000 }: TunnelStatusProps) {
  const [status, setStatus] = useState<TunnelStatusData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      const res = await fetch("/api/tunnel/status", { signal: AbortSignal.timeout(5000) });
      if (!res.ok) throw new Error("Failed to fetch tunnel status");
      const data = await res.json();
      setStatus(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, refreshInterval);
    return () => clearInterval(interval);
  }, [refreshInterval]);

  if (isLoading) {
    return (
      <div className={cn("flex items-center gap-2 text-sm text-muted-foreground", className)}>
        <div className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse" />
        <span>Loading...</span>
      </div>
    );
  }

  if (error || status?.fallback_mode) {
    return (
      <div className={cn("flex items-center gap-2 text-sm text-yellow-500", className)}>
        <div className="w-2 h-2 rounded-full bg-yellow-500" />
        <span>{error || "Fallback Mode"}</span>
      </div>
    );
  }

  if (!status?.key) {
    return (
      <div className={cn("flex items-center gap-2 text-sm text-red-500", className)}>
        <div className="w-2 h-2 rounded-full bg-red-500" />
        <span>No Key Configured</span>
      </div>
    );
  }

  const isHealthy = status.health?.status === "ok";
  const keyLabel = `Key ${status.key.current_key_index + 1}/${status.key.total_keys}`;

  return (
    <div className={cn("flex items-center gap-4 text-sm", className)}>
      <div className="flex items-center gap-2">
        <div className={cn("w-2 h-2 rounded-full", isHealthy ? "bg-green-500" : "bg-yellow-500")} />
        <span className="text-muted-foreground">Tunnel:</span>
        <span className="font-medium">{status.key.provider}</span>
      </div>
      <div className="text-xs text-muted-foreground">{keyLabel}</div>
      {status.model?.current && (
        <div className="text-xs text-muted-foreground">
          Model: {status.model.current.split("/").pop()}
        </div>
      )}
      {status.health?.latency_ms && (
        <div className="text-xs text-muted-foreground">
          {status.health.latency_ms}ms
        </div>
      )}
    </div>
  );
}