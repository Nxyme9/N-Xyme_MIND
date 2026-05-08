export const dynamic = 'force-static';
import { NextRequest, NextResponse } from "next/server";
import { config } from "@/lib/config";

const BACKEND_URL = config.backend.httpGateway;

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

interface TaskChainResponse {
  status: string;
  execution_id?: string;
  results?: Array<{
    node_id: string;
    agent: string;
    status: "pending" | "running" | "completed" | "failed";
    result?: unknown;
    error?: string;
    duration_ms?: number;
    outputs?: Record<string, unknown>;
  }>;
  error?: string;
}

function buildExecutionPlan(
  nodes: WorkflowNode[],
  edges: WorkflowEdge[]
): { batches: string[][]; node_map: Map<string, WorkflowNode> } {
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));
  const inDegree = new Map<string, number>();
  const adjList = new Map<string, string[]>();

  for (const node of nodes) {
    inDegree.set(node.id, 0);
    adjList.set(node.id, []);
  }

  for (const edge of edges) {
    const current = inDegree.get(edge.target) || 0;
    inDegree.set(edge.target, current + 1);
    const neighbors = adjList.get(edge.source) || [];
    neighbors.push(edge.target);
    adjList.set(edge.source, neighbors);
  }

  const batches: string[][] = [];
  const remaining = new Set(nodes.map((n) => n.id));

  while (remaining.size > 0) {
    const batch: string[] = [];
    for (const nodeId of remaining) {
      if ((inDegree.get(nodeId) || 0) === 0) {
        batch.push(nodeId);
      }
    }

    if (batch.length === 0) {
      break;
    }

    batches.push(batch);

    for (const nodeId of batch) {
      remaining.delete(nodeId);
      const neighbors = adjList.get(nodeId) || [];
      for (const neighbor of neighbors) {
        const currentDegree = inDegree.get(neighbor) || 0;
        inDegree.set(neighbor, currentDegree - 1);
      }
    }
  }

  return { batches, node_map: nodeMap };
}

function shouldExecuteInBatch(
  edge: WorkflowEdge,
  previousResult: unknown
): boolean {
  if (!edge.condition) return true;
  if (edge.type !== "conditional") return true;

  const outputs = previousResult as Record<string, unknown>;
  const outputValue = outputs?.[edge.condition.output_key || "status"];

  switch (edge.condition.operator) {
    case "equals":
      return outputValue === edge.condition.value;
    case "contains":
      return String(outputValue).includes(edge.condition.value || "");
    case "greater_than":
      return Number(outputValue) > Number(edge.condition.value);
    case "less_than":
      return Number(outputValue) < Number(edge.condition.value);
    default:
      return true;
  }
}

export async function POST(request: NextRequest) {
  try {
    const body: WorkflowDefinition = await request.json();
    const { nodes, edges, execution_mode, config: execConfig } = body;

    if (!nodes || !Array.isArray(nodes) || nodes.length === 0) {
      return NextResponse.json(
        { status: "error", error: "Workflow must have at least one node" },
        { status: 400 }
      );
    }

    const executionId = `exec_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
    const results: TaskChainResponse["results"] = [];
    const nodeOutputs = new Map<string, unknown>();

    if (execution_mode === "parallel") {
      const parallelPromises = nodes.map(async (node) => {
        const startTime = Date.now();
        try {
          const response = await fetch(`${BACKEND_URL}/orchestration_spawn`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              agent: node.agent,
              task: node.task,
              context: node.context || "",
              ...node.config,
            }),
            signal: AbortSignal.timeout(node.config?.timeout_ms || 30000),
          });

          const durationMs = Date.now() - startTime;
          const data = await response.json();
          nodeOutputs.set(node.id, data);

          return {
            node_id: node.id,
            agent: node.agent,
            status: response.ok ? "completed" : "failed",
            result: data,
            error: response.ok ? undefined : `HTTP ${response.status}`,
            duration_ms: durationMs,
            outputs: data,
          };
        } catch (e) {
          return {
            node_id: node.id,
            agent: node.agent,
            status: "failed",
            error: e instanceof Error ? e.message : "Unknown error",
            duration_ms: Date.now() - startTime,
          };
        }
      });

      const parallelResults = await Promise.all(parallelPromises);
      return NextResponse.json({
        status: "ok",
        execution_id: executionId,
        results: parallelResults,
      });
    }

    const { batches, node_map } = buildExecutionPlan(nodes, edges || []);
    const failFast = execConfig?.fail_fast ?? true;

    for (const batchOfNodes of batches) {
      const batchResults = await Promise.all(
        batchOfNodes.map(async (nodeId) => {
          const node = node_map.get(nodeId);
          if (!node) return null;

          const startTime = Date.now();
          const incomingEdges = edges.filter((e) => e.target === nodeId);
          let enrichedContext = node.context || "";

          for (const edge of incomingEdges) {
            const prevOutput = nodeOutputs.get(edge.source);
            if (prevOutput && shouldExecuteInBatch(edge, prevOutput)) {
              enrichedContext += `\n\n--- Previous Output (${edge.source}) ---\n${JSON.stringify(prevOutput, null, 2)}`;
            }
          }

          try {
            const response = await fetch(`${BACKEND_URL}/orchestration_spawn`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                agent: node.agent,
                task: node.task,
                context: enrichedContext,
                ...node.config,
              }),
              signal: AbortSignal.timeout(node.config?.timeout_ms || 30000),
            });

            const durationMs = Date.now() - startTime;
            const data = await response.json();
            nodeOutputs.set(node.id, data);

            return {
              node_id: node.id,
              agent: node.agent,
              status: (response.ok ? "completed" : "failed") as "completed" | "failed",
              result: data,
              error: response.ok ? undefined : `HTTP ${response.status}`,
              duration_ms: durationMs,
              outputs: data,
            };
          } catch (e) {
            return {
              node_id: node.id,
              agent: node.agent,
              status: "failed" as const,
              error: e instanceof Error ? e.message : "Unknown error",
              duration_ms: Date.now() - startTime,
            };
          }
        })
      );

      for (const result of batchResults) {
        if (result) {
          results.push(result);
          if (result.status === "failed" && failFast) {
            return NextResponse.json({
              status: "partial",
              execution_id: executionId,
              results,
              error: `Failed at node ${result.node_id}, aborting due to fail_fast=true`,
            });
          }
        }
      }
    }

    return NextResponse.json({
      status: "ok",
      execution_id: executionId,
      results,
    });
  } catch (e: unknown) {
    return NextResponse.json(
      { status: "error", error: e instanceof Error ? e.message : "Internal error" },
      { status: 500 }
    );
  }
}

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/orchestration_task_status`, {
      signal: AbortSignal.timeout(5000),
    });

    if (!response.ok) {
      return NextResponse.json({ status: "error", error: "Backend unavailable" }, { status: 502 });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ status: "error", error: "Failed to connect to backend" }, { status: 500 });
  }
}