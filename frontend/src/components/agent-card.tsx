"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Agent } from "@/stores/useAgentStore";

interface AgentCardProps {
  agent: Agent;
}

const statusColors = {
  idle: "bg-green-500",
  working: "bg-blue-500",
  error: "bg-red-500",
};

const statusLabels = {
  idle: "Idle",
  working: "Working",
  error: "Error",
};

export function AgentCard({ agent }: AgentCardProps) {
  return (
    <Card className="w-full card-hover cursor-pointer">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{agent.name}</CardTitle>
          <Badge
            className={`${statusColors[agent.status]} text-white border-0`}
          >
            {statusLabels[agent.status]}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        {agent.currentTask ? (
          <span className="text-sm text-muted-foreground">
            Current task: {agent.currentTask}
          </span>
        ) : (
          <span className="text-sm text-muted-foreground">No active task</span>
        )}
        {agent.lastActive && (
          <div className="text-xs text-muted-foreground mt-2">
            Last active: {new Date(agent.lastActive).toLocaleTimeString()}
          </div>
        )}
      </CardContent>
    </Card>
  );
}