export const dynamic = 'force-static';
import { NextRequest, NextResponse } from "next/server";
import { config } from "@/lib/config";

const BACKEND_URL = config.backend.httpGateway;

export interface MCPConnection {
  name: string;
  status: "connected" | "disconnected" | "error";
  lastPing?: string;
  type?: string;
  config?: Record<string, string>;
}

const DEFAULT_MCPS: MCPConnection[] = [
  { name: "Sequential Thinking", status: "connected" },
  { name: "Memory", status: "connected" },
  { name: "Context7", status: "connected" },
  { name: "Filesystem", status: "connected" },
  { name: "GitHub", status: "connected" },
  { name: "Notion", status: "connected" },
  { name: "Telegram", status: "connected" },
];

const REGISTERED_MCPS: MCPConnection[] = [...DEFAULT_MCPS];

interface MCPResponse {
  connections: MCPConnection[];
  backendAvailable: boolean;
  timestamp: string;
}

export async function GET(): Promise<NextResponse<MCPResponse>> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    try {
      const response = await fetch(`${BACKEND_URL}/tools_list`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        const data = await response.json();
        const tools = data.agents || data.data || [];
        
        const packageMap = new Map<string, string[]>();
        tools.forEach((tool: any) => {
          const pkg = tool.package || "unknown";
          if (!packageMap.has(pkg)) {
            packageMap.set(pkg, []);
          }
          packageMap.get(pkg)!.push(tool.name);
        });

        const connections: MCPConnection[] = Array.from(packageMap.entries()).map(([name, toolNames]) => ({
          name: name.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase()),
          status: "connected" as const,
          lastPing: new Date().toISOString(),
          type: "package",
        }));

        return NextResponse.json({
          connections,
          backendAvailable: true,
          timestamp: new Date().toISOString(),
        });
      }
    } catch {
      clearTimeout(timeoutId);
    }

    return NextResponse.json({
      connections: DEFAULT_MCPS as MCPConnection[],
      backendAvailable: false,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error fetching MCP status:", error);
    return NextResponse.json(
      {
        connections: DEFAULT_MCPS as MCPConnection[],
        backendAvailable: false,
        timestamp: new Date().toISOString(),
      },
      { status: 200 }
    );
  }
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  try {
    const body = await request.json();
    const { name, type, config: mcpConfig } = body;

    if (!name || !type) {
      return NextResponse.json(
        { error: "MCP name and type are required" },
        { status: 400 }
      );
    }

    const existing = REGISTERED_MCPS.find(
      (m) => m.name.toLowerCase() === name.toLowerCase()
    );

    if (existing) {
      return NextResponse.json(
        { error: `MCP "${name}" already exists` },
        { status: 409 }
      );
    }

    const newMCP: MCPConnection = {
      name,
      status: "connected",
      lastPing: new Date().toISOString(),
      type,
      config: mcpConfig || {},
    };

    REGISTERED_MCPS.push(newMCP);

    return NextResponse.json({
      success: true,
      mcp: newMCP,
      connections: REGISTERED_MCPS,
    });
  } catch (error) {
    console.error("Error registering MCP:", error);
    return NextResponse.json(
      { error: "Failed to register MCP" },
      { status: 500 }
    );
  }
}

export async function PUT(request: NextRequest): Promise<NextResponse> {
  try {
    const body = await request.json();
    const { name, status, config: mcpConfig } = body;

    if (!name) {
      return NextResponse.json(
        { error: "MCP name is required" },
        { status: 400 }
      );
    }

    const mcp = REGISTERED_MCPS.find(
      (m) => m.name.toLowerCase() === name.toLowerCase()
    );

    if (!mcp) {
      return NextResponse.json(
        { error: `MCP "${name}" not found` },
        { status: 404 }
      );
    }

    if (status) {
      mcp.status = status;
    }
    if (mcpConfig) {
      mcp.config = { ...mcp.config, ...mcpConfig };
    }
    mcp.lastPing = new Date().toISOString();

    return NextResponse.json({
      success: true,
      mcp,
      connections: REGISTERED_MCPS,
    });
  } catch (error) {
    console.error("Error updating MCP:", error);
    return NextResponse.json(
      { error: "Failed to update MCP" },
      { status: 500 }
    );
  }
}

export async function DELETE(request: NextRequest): Promise<NextResponse> {
  try {
    const { searchParams } = new URL(request.url);
    const name = searchParams.get("name");

    if (!name) {
      return NextResponse.json(
        { error: "MCP name is required" },
        { status: 400 }
      );
    }

    const index = REGISTERED_MCPS.findIndex(
      (m) => m.name.toLowerCase() === name.toLowerCase()
    );

    if (index === -1) {
      return NextResponse.json(
        { error: `MCP "${name}" not found` },
        { status: 404 }
      );
    }

    const DEFAULT_NAMES = DEFAULT_MCPS.map((m) => m.name.toLowerCase());
    if (DEFAULT_NAMES.includes(name.toLowerCase())) {
      return NextResponse.json(
        { error: `Cannot delete default MCP "${name}"` },
        { status: 403 }
      );
    }

    REGISTERED_MCPS.splice(index, 1);

    return NextResponse.json({
      success: true,
      connections: REGISTERED_MCPS,
    });
  } catch (error) {
    console.error("Error deleting MCP:", error);
    return NextResponse.json(
      { error: "Failed to delete MCP" },
      { status: 500 }
    );
  }
}