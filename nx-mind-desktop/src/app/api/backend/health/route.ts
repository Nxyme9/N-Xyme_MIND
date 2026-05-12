import { NextResponse } from "next/server";

interface HealthStatus {
  status: "healthy" | "degraded" | "unhealthy";
  backend: {
    orchestration: boolean;
    unifiedMcp: boolean;
    intelligence: boolean;
  };
  timestamp: string;
  version: string;
}

interface HealthResponse extends HealthStatus {
  checks: {
    agents: boolean;
    mcp: boolean;
    settings: boolean;
  };
}

async function checkService(url: string): Promise<boolean> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 2000);

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return response.ok;
  } catch {
    clearTimeout(timeoutId);
    return false;
  }
}

export async function GET(): Promise<NextResponse<HealthResponse>> {
  const startTime = Date.now();
  
  const [mcpOk, gatewayOk] = await Promise.all([
    checkService("http://localhost:8765/memory_stats"),
    checkService("http://localhost:8766/system_health_check"),
  ]);

  const [agentsOk, mcpRegistryOk] = await Promise.all([
    fetch("http://localhost:8766/api/agents", { method: "GET" })
      .then((r) => r.ok)
      .catch(() => false),
    fetch("http://localhost:8766/api/mcp", { method: "GET" })
      .then((r) => r.ok)
      .catch(() => false),
  ]);

  const backendCount = [mcpOk, gatewayOk].filter(Boolean).length;
  const apiCount = [agentsOk, mcpRegistryOk].filter(Boolean).length;

  let status: "healthy" | "degraded" | "unhealthy";
  if (backendCount >= 1 || apiCount >= 1) {
    status = "degraded";
  } else {
    status = "unhealthy";
  }

  const response: HealthResponse = {
    status,
    backend: {
      orchestration: gatewayOk,
      unifiedMcp: mcpOk,
      intelligence: mcpOk,
    },
    checks: {
      agents: agentsOk,
      mcp: mcpRegistryOk,
      settings: mcpOk,
    },
    timestamp: new Date().toISOString(),
    version: "1.0.0",
  };

  const responseTime = Date.now() - startTime;
  
  return NextResponse.json(response, {
    headers: {
      "X-Response-Time": `${responseTime}ms`,
    },
  });
}