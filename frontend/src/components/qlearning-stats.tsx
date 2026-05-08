"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface AgentStats {
  agent: string;
  successRate: number;
  avgLatency: number;
  totalTasks: number;
}

interface QLearningStatsData {
  routing_weights?: Record<string, number>;
  agent_performance?: AgentStats[];
  ab_tests?: Record<string, { variant_a: number; variant_b: number }>;
}

interface QLearningStatsProps {
  className?: string;
  refreshInterval?: number;
}

export function QLearningStats({ className, refreshInterval = 60000 }: QLearningStatsProps) {
  const [stats, setStats] = useState<QLearningStatsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch("/api/learning/status", { signal: AbortSignal.timeout(5000) });
        if (res.ok) {
          const data = await res.json();
          setStats(data);
        }
      } catch (e) {
        console.error("Failed to fetch Q-Learning stats:", e);
      } finally {
        setIsLoading(false);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, refreshInterval);
    return () => clearInterval(interval);
  }, [refreshInterval]);

  if (isLoading) {
    return (
      <Card className={cn("", className)}>
        <CardContent className="p-4">
          <p className="text-sm text-muted-foreground">Loading...</p>
        </CardContent>
      </Card>
    );
  }

  if (!stats?.agent_performance || stats.agent_performance.length === 0) {
    return (
      <Card className={cn("", className)}>
        <CardContent className="p-4">
          <p className="text-sm text-muted-foreground">No routing data yet</p>
        </CardContent>
      </Card>
    );
  }

  const getSuccessColor = (rate: number) => {
    if (rate >= 0.8) return "text-green-500";
    if (rate >= 0.5) return "text-yellow-500";
    return "text-red-500";
  };

  return (
    <Card className={cn("", className)}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">Q-Learning Routing</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {stats.agent_performance.map((agent) => (
          <div key={agent.agent} className="flex items-center justify-between">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{agent.agent}</p>
              <p className="text-xs text-muted-foreground">{agent.totalTasks} tasks</p>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className={cn("text-sm font-mono", getSuccessColor(agent.successRate))}>
                  {(agent.successRate * 100).toFixed(0)}%
                </p>
                <p className="text-xs text-muted-foreground">success</p>
              </div>
              <div className="text-right">
                <p className="text-sm font-mono">{agent.avgLatency}ms</p>
                <p className="text-xs text-muted-foreground">latency</p>
              </div>
            </div>
          </div>
        ))}
        {stats.routing_weights && (
          <div className="pt-2 border-t">
            <p className="text-xs text-muted-foreground mb-2">Routing Weights</p>
            <div className="flex flex-wrap gap-1">
              {Object.entries(stats.routing_weights).map(([key, weight]) => (
                <span
                  key={key}
                  className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-muted"
                >
                  {key}: {weight.toFixed(2)}
                </span>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function QLearningStatsMini() {
  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
      <span>QLearning Active</span>
    </div>
  );
}