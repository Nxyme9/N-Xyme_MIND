"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { ArrowRight, Clock, CheckCircle, XCircle, Loader2, RefreshCw } from "lucide-react";

interface RoutingEntry {
  id: string;
  task: string;
  level: number;
  agents: string[];
  status: "completed" | "running" | "failed";
  duration: string;
  timestamp: Date;
  error?: string;
}

const fallbackData: RoutingEntry[] = [
  { id: "route-1", task: "Implement JWT auth", level: 3, agents: ["sisyphus", "prometheus", "hephaestus"], status: "completed", duration: "2.3s", timestamp: new Date(Date.now() - 1000 * 60 * 5) },
  { id: "route-2", task: "Fix memory leak", level: 4, agents: ["sisyphus", "oracle", "hephaestus"], status: "completed", duration: "1.1s", timestamp: new Date(Date.now() - 1000 * 60 * 2) },
  { id: "route-3", task: "Add unit tests", level: 2, agents: ["sisyphus", "atlas"], status: "completed", duration: "0.8s", timestamp: new Date(Date.now() - 1000 * 60 * 15) },
  { id: "route-4", task: "Update documentation", level: 1, agents: ["sisyphus", "sisyphus-junior"], status: "failed", duration: "0.3s", timestamp: new Date(Date.now() - 1000 * 60 * 30), error: "Permission denied" },
  { id: "route-5", task: "Research React patterns", level: 3, agents: ["sisyphus", "explore", "librarian"], status: "completed", duration: "3.2s", timestamp: new Date(Date.now() - 1000 * 60 * 45) },
];

const agentColors: Record<string, string> = {
  sisyphus: "bg-yellow-500",
  prometheus: "bg-orange-500",
  oracle: "bg-blue-500",
  hephaestus: "bg-green-500",
  explore: "bg-purple-500",
  librarian: "bg-pink-500",
  atlas: "bg-cyan-500",
  "sisyphus-junior": "bg-gray-500",
  metis: "bg-indigo-500",
  momus: "bg-red-500",
};

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case "completed": return <CheckCircle className="w-4 h-4 text-green-500" />;
    case "running": return <Loader2 className="w-4 h-4 text-yellow-500 animate-spin" />;
    case "failed": return <XCircle className="w-4 h-4 text-red-500" />;
    default: return <Clock className="w-4 h-4 text-gray-500" />;
  }
}

function AgentBadge({ name }: { name: string }) {
  const color = agentColors[name] || "bg-gray-500";
  return <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium text-white ${color}`}>{name}</span>;
}

export default function RouteViz() {
  const [routingHistory, setRoutingHistory] = useState<RoutingEntry[]>(fallbackData);
  const [loading, setLoading] = useState(true);
  const [dataSource, setDataSource] = useState<"live" | "fallback">("fallback");

  useEffect(() => {
    async function fetchOutcomes() {
      try {
        const res = await fetch("/api/learning/outcomes?limit=20");
        if (res.ok) {
          const data = await res.json();
          if (data.outcomes && data.outcomes.length > 0) {
            const mapped: RoutingEntry[] = data.outcomes.map((o: any) => ({
              id: o.task_id || o.id || `outcome-${Date.now()}`,
              task: o.task || o.task_description || "Task",
              level: o.level || 3,
              agents: o.agent ? [o.agent] : [],
              status: o.success ? "completed" : "failed",
              duration: o.latency_ms ? `${(o.latency_ms / 1000).toFixed(1)}s` : "0s",
              timestamp: new Date(o.timestamp || Date.now()),
              error: o.error,
            }));
            setRoutingHistory(mapped);
            setDataSource("live");
          }
        }
      } catch (e) {
        console.error("Route outcomes fetch failed:", e);
      }
      setLoading(false);
    }
    fetchOutcomes();
  }, []);

  const completedCount = routingHistory.filter((r) => r.status === "completed").length;
  const failedCount = routingHistory.filter((r) => r.status === "failed").length;
  const avgDuration = routingHistory.length > 0 
    ? routingHistory.reduce((acc, r) => acc + parseFloat(r.duration || "0"), 0) / routingHistory.length 
    : 0;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium">Routing History</CardTitle>
        <div className="flex items-center gap-2">
          {dataSource === "live" ? (
            <span className="text-xs px-2 py-0.5 rounded-full bg-green-500/20 text-green-400">Live</span>
          ) : (
            <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-500/20 text-yellow-400">Fallback</span>
          )}
          <button onClick={() => window.location.reload()} className="p-1 hover:bg-slate-800 rounded">
            <RefreshCw className="w-3 h-3" />
          </button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <div className="text-2xl font-bold">{routingHistory.length}</div>
            <div className="text-xs text-muted-foreground">Total Routes</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-green-500">{completedCount}</div>
            <div className="text-xs text-muted-foreground">Completed</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-red-500">{failedCount}</div>
            <div className="text-xs text-muted-foreground">Failed</div>
          </div>
        </div>
        <div className="space-y-2">
          {loading ? (
            <div className="text-sm text-muted-foreground">Loading...</div>
          ) : (
            routingHistory.slice(0, 5).map((route) => (
              <div key={route.id} className="flex items-center gap-2 p-2 rounded bg-slate-900/50">
                <StatusIcon status={route.status} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{route.task}</div>
                  <div className="flex items-center gap-1 mt-1">
                    {route.agents.map((a) => <AgentBadge key={a} name={a} />)}
                  </div>
                </div>
                <div className="text-xs text-muted-foreground">{route.duration}</div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}