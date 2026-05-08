"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronRight, Users, Activity, Clock, Zap } from "lucide-react";
import { useState } from "react";

// Define the delegation chain structure
interface DelegationNode {
  id: string;
  name: string;
  role: string;
  status: "idle" | "working" | "completed" | "failed";
  tasksCompleted: number;
  totalTasks: number;
  children?: DelegationNode[];
}

// Sample delegation chain
const delegationChain: DelegationNode = {
  id: "sisyphus",
  name: "Sisyphus",
  role: "Orchestrator",
  status: "working",
  tasksCompleted: 12,
  totalTasks: 15,
  children: [
    {
      id: "prometheus",
      name: "Prometheus",
      role: "Plan Builder",
      status: "completed",
      tasksCompleted: 5,
      totalTasks: 5,
      children: [
        { id: "hephaestus", name: "Hephaestus", role: "Implementer", status: "completed", tasksCompleted: 3, totalTasks: 3 },
        { id: "atlas", name: "Atlas", role: "Executor", status: "completed", tasksCompleted: 2, totalTasks: 2 },
      ],
    },
    {
      id: "oracle",
      name: "Oracle",
      role: "Architecture Review",
      status: "working",
      tasksCompleted: 2,
      totalTasks: 4,
      children: [
        { id: "momus", name: "Momus", role: "Red Team", status: "idle", tasksCompleted: 0, totalTasks: 2 },
      ],
    },
    {
      id: "explore",
      name: "Explore",
      role: "Codebase Search",
      status: "completed",
      tasksCompleted: 3,
      totalTasks: 3,
    },
    {
      id: "librarian",
      name: "Librarian",
      role: "External Research",
      status: "completed",
      tasksCompleted: 2,
      totalTasks: 2,
    },
  ],
};

// Agent icons and colors
const agentConfig: Record<string, { icon: string; color: string; bg: string }> = {
  sisyphus: { icon: "S", color: "text-yellow-500", bg: "bg-yellow-500" },
  prometheus: { icon: "P", color: "text-orange-500", bg: "bg-orange-500" },
  oracle: { icon: "O", color: "text-blue-500", bg: "bg-blue-500" },
  hephaestus: { icon: "H", color: "text-green-500", bg: "bg-green-500" },
  atlas: { icon: "A", color: "text-cyan-500", bg: "bg-cyan-500" },
  momus: { icon: "M", color: "text-red-500", bg: "bg-red-500" },
  explore: { icon: "E", color: "text-purple-500", bg: "bg-purple-500" },
  librarian: { icon: "L", color: "text-pink-500", bg: "bg-pink-500" },
};

function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    idle: "outline",
    working: "secondary",
    completed: "default",
    failed: "destructive",
  };
  
  const colors: Record<string, string> = {
    working: "bg-yellow-500",
    completed: "bg-green-500",
    failed: "bg-red-500",
    idle: "",
  };

  return (
    <Badge 
      variant={variants[status] || "outline"} 
      className={`${colors[status]} border-0 text-white`}
    >
      {status}
    </Badge>
  );
}

function DelegationNodeItem({ 
  node, 
  depth = 0,
  isLast = true 
}: { 
  node: DelegationNode; 
  depth?: number;
  isLast?: boolean;
}) {
  const [expanded, setExpanded] = useState(depth < 2);
  const hasChildren = node.children && node.children.length > 0;
  const config = agentConfig[node.id] || { icon: "?", color: "text-gray-500", bg: "bg-gray-500" };
  
  const progress = node.totalTasks > 0 ? (node.tasksCompleted / node.totalTasks) * 100 : 0;

  return (
    <div className="select-none">
      <div 
        className="flex items-center gap-2 py-2 px-3 rounded-lg hover:bg-muted/50 transition-colors cursor-pointer"
        style={{ paddingLeft: `${depth * 20 + 12}px` }}
        onClick={() => hasChildren && setExpanded(!expanded)}
      >
        {/* Expand/Collapse Icon */}
        {hasChildren ? (
          expanded ? (
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="w-4 h-4 text-muted-foreground" />
          )
        ) : (
          <div className="w-4" />
        )}

        {/* Agent Avatar */}
        <Avatar className="w-8 h-8">
          <AvatarFallback className={`${config.bg} text-white text-sm`}>
            {config.icon}
          </AvatarFallback>
        </Avatar>

        {/* Agent Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm">{node.name}</span>
            <span className="text-xs text-muted-foreground">({node.role})</span>
          </div>
          
          {/* Progress Bar */}
          <div className="flex items-center gap-2 mt-1">
            <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
              <div 
                className={`h-full ${config.bg}`} 
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="text-xs text-muted-foreground">
              {node.tasksCompleted}/{node.totalTasks}
            </span>
          </div>
        </div>

        {/* Status */}
        <StatusBadge status={node.status} />
      </div>

      {/* Children */}
      {hasChildren && expanded && (
        <div>
          {node.children!.map((child, idx) => (
            <DelegationNodeItem 
              key={child.id} 
              node={child} 
              depth={depth + 1}
              isLast={idx === node.children!.length - 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function DelegationChain() {
  // Calculate stats
  const allAgents = delegationChain.children || [];
  const workingCount = allAgents.filter((a) => a.status === "working").length;
  const completedCount = allAgents.filter((a) => a.status === "completed").length;
  const idleCount = allAgents.filter((a) => a.status === "idle").length;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Users className="w-5 h-5" />
            Agent Delegation Chain
          </CardTitle>
          <div className="flex gap-2">
            <Badge variant="secondary" className="bg-yellow-500/20 text-yellow-500 border-0">
              {workingCount} active
            </Badge>
            <Badge variant="default" className="bg-green-500 border-0">
              {completedCount} done
            </Badge>
            <Badge variant="outline">
              {idleCount} idle
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Root Node */}
        <div className="flex items-center gap-3 p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/30 mb-4">
          <Avatar className="w-10 h-10">
            <AvatarFallback className="bg-yellow-500 text-white">
              S
            </AvatarFallback>
          </Avatar>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold">{delegationChain.name}</span>
              <span className="text-sm text-muted-foreground">({delegationChain.role})</span>
            </div>
            <div className="flex items-center gap-2 mt-1">
              <Activity className="w-3 h-3 text-yellow-500" />
              <span className="text-xs text-muted-foreground">
                {delegationChain.tasksCompleted} of {delegationChain.totalTasks} tasks
              </span>
            </div>
          </div>
          <StatusBadge status={delegationChain.status} />
        </div>

        {/* Delegation Tree */}
        <div className="border rounded-lg p-2">
          {delegationChain.children?.map((child, idx) => (
            <DelegationNodeItem 
              key={child.id} 
              node={child}
              isLast={idx === (delegationChain.children?.length || 0) - 1}
            />
          ))}
        </div>

        {/* Legend */}
        <div className="mt-4 pt-4 border-t flex items-center gap-6 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <Zap className="w-3 h-3" />
            <span>Click to expand/collapse</span>
          </div>
          <div className="flex items-center gap-2">
            <Clock className="w-3 h-3" />
            <span>Progress shows tasks completed</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}