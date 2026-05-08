export const dynamic = 'force-static';
import { NextResponse } from "next/server";
import { config } from "@/lib/config";

const BACKEND_URL = config.backend.httpGateway;

const DEFAULT_AGENTS: Agent[] = [
  { id: "sisyphus", name: "Sisyphus", status: "idle" },
  { id: "hephaestus", name: "Hephaestus", status: "idle" },
  { id: "oracle", name: "Oracle", status: "idle" },
  { id: "prometheus", name: "Prometheus", status: "idle" },
  { id: "metis", name: "Metis", status: "idle" },
  { id: "momus", name: "Momus", status: "idle" },
  { id: "atlas", name: "Atlas", status: "idle" },
  { id: "explore", name: "Explore", status: "idle" },
  { id: "librarian", name: "Librarian", status: "idle" },
  { id: "plan", name: "Plan", status: "idle" },
  { id: "multimodal_looker", name: "Multimodal Looker", status: "idle" },
];

export interface Agent {
  id: string;
  name: string;
  status: "idle" | "working" | "error";
  currentTask?: string;
  lastActive?: string;
}

interface AgentsResponse {
  agents: Agent[];
  backendAvailable: boolean;
  timestamp: string;
}

export async function GET(): Promise<NextResponse<AgentsResponse>> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    try {
      const response = await fetch(`${BACKEND_URL}/api/registry/agents`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        const data = await response.json();
        if (data.data && Array.isArray(data.data)) {
          return NextResponse.json({
            agents: data.data.map((agent: { id?: string; name?: string; role?: string }) => ({
              id: agent.id || agent.name?.toLowerCase().replace(/\s+/g, "_") || "unknown",
              name: agent.name || agent.id || "Unknown",
              status: "idle" as const,
            })),
            backendAvailable: true,
            timestamp: new Date().toISOString(),
          });
        }
      }
    } catch {
      clearTimeout(timeoutId);
    }

    return NextResponse.json({
      agents: DEFAULT_AGENTS,
      backendAvailable: false,
      timestamp: new Date().toISOString(),
    });
  } catch (e: unknown) {
    return NextResponse.json(
      {
        agents: DEFAULT_AGENTS,
        backendAvailable: false,
        timestamp: new Date().toISOString(),
        error: e instanceof Error ? e.message : "Internal error",
      },
      { status: 200 }
    );
  }
}