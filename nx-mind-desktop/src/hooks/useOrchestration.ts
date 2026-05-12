"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";

const API_BASE = "";

// Types
interface OrchestrationTool {
  name: string;
  description?: string;
  category?: string;
}

interface OrchestrationToolsResponse {
  status: string;
  data?: {
    tools?: OrchestrationTool[];
    [key: string]: unknown;
  };
}

interface TaskStatus {
  task_id: string;
  status: "pending" | "running" | "completed" | "failed";
  result?: unknown;
  error?: string;
}

interface TaskStatusResponse {
  status: string;
  data?: TaskStatus;
}

interface SessionState {
  current_task?: string;
  active_tasks?: string[];
  [key: string]: unknown;
}

interface SessionResponse {
  status: string;
  data?: SessionState;
}

// Fetch available tools
async function fetchTools(): Promise<OrchestrationToolsResponse> {
  try {
    const response = await fetch(`${API_BASE}/api/orchestration/tools`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  } catch (error) {
    console.error("Failed to fetch tools:", error);
    return { status: "error", data: { tools: [] } };
  }
}

// Fetch session state
async function fetchSessionState(): Promise<SessionResponse> {
  try {
    const response = await fetch(`${API_BASE}/api/orchestration/session`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  } catch (error) {
    console.error("Failed to fetch session state:", error);
    return { status: "error", data: {} };
  }
}

// Fetch task status
async function fetchTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  try {
    const response = await fetch(`${API_BASE}/api/orchestration/status/${taskId}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  } catch (error) {
    console.error(`Failed to fetch task status for ${taskId}:`, error);
    return { status: "error", data: undefined };
  }
}

// Spawn agent task
async function spawnAgent(agent: string, task: string, context: string = ""): Promise<{ status: string; data?: { task_id?: string } }> {
  try {
    const response = await fetch(`${API_BASE}/api/orchestration/spawn`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ agent, task, context }),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  } catch (error) {
    console.error("Failed to spawn agent:", error);
    return { status: "error" };
  }
}

export function useOrchestrationTools() {
  const query = useQuery({
    queryKey: ["orchestrationTools"],
    queryFn: fetchTools,
    refetchInterval: 30000, // 30s - tools don't change often
    staleTime: 15000,
  });

  return {
    tools: query.data?.data?.tools || [],
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
}

export function useSessionState() {
  const query = useQuery({
    queryKey: ["sessionState"],
    queryFn: fetchSessionState,
    refetchInterval: 10000,
  });

  return {
    session: query.data?.data,
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: query.refetch,
  };
}

export function useCatalystState() {
  const query = useQuery({
    queryKey: ["catalystState"],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/api/orchestration/session`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ user_input: "status check" }) });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    },
    refetchInterval: 30000,
  });

  return {
    state: query.data?.data?.state || "unknown",
    confidence: query.data?.data?.confidence || 0,
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: query.refetch,
  };
}

export function useTaskStatus(taskId: string | null) {
  const query = useQuery({
    queryKey: ["taskStatus", taskId],
    queryFn: () => fetchTaskStatus(taskId!),
    enabled: !!taskId,
    refetchInterval: 5000, // 5s for active tasks
  });

  return {
    status: query.data?.data,
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: query.refetch,
  };
}

export function useSpawnAgent() {
  return useMutation({
    mutationFn: ({ agent, task, context }: { agent: string; task: string; context?: string }) =>
      spawnAgent(agent, task, context || ""),
  });
}

interface TaskChainItem {
  agent: string;
  task: string;
  context?: string;
}

interface WorkflowNode {
  id: string;
  agent: string;
  task: string;
  context?: string;
  config?: {
    timeout_ms?: number;
    max_retries?: number;
    model?: string;
    temperature?: number;
  };
}

interface WorkflowEdge {
  source: string;
  target: string;
  type?: "sequential" | "conditional";
  condition?: {
    output_key?: string;
    operator?: "equals" | "contains" | "greater_than" | "less_than";
    value?: string;
  };
}

interface WorkflowDefinition {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  execution_mode: "linear" | "parallel" | "dag";
  config?: {
    fail_fast?: boolean;
    max_parallel_tasks?: number;
  };
}

interface TaskChainResult {
  node_id?: string;
  agent: string;
  status: string;
  result?: unknown;
  error?: string;
  duration_ms?: number;
}

interface TaskChainResponse {
  status: string;
  execution_id?: string;
  results?: TaskChainResult[];
  error?: string;
}

async function executeTaskChain(
  chain: TaskChainItem[],
  mode: "linear" | "parallel"
): Promise<TaskChainResponse> {
  try {
    const response = await fetch(`${API_BASE}/api/orchestration/chain`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chain, mode }),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  } catch (error) {
    console.error("Failed to execute task chain:", error);
    return { status: "error", error: error instanceof Error ? error.message : "Unknown error" };
  }
}

async function executeWorkflow(workflow: WorkflowDefinition): Promise<TaskChainResponse> {
  try {
    const response = await fetch(`${API_BASE}/api/orchestration/chain`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(workflow),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  } catch (error) {
    console.error("Failed to execute workflow:", error);
    return { status: "error", error: error instanceof Error ? error.message : "Unknown error" };
  }
}

export function useTaskChain() {
  return useMutation({
    mutationFn: ({ chain, mode }: { chain: TaskChainItem[]; mode: "linear" | "parallel" }) =>
      executeTaskChain(chain, mode),
  });
}

export function useWorkflowExecution() {
  return useMutation({
    mutationFn: (workflow: WorkflowDefinition) => executeWorkflow(workflow),
  });
}