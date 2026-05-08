export const dynamic = 'force-static';
import { NextRequest, NextResponse } from "next/server";
import { config } from "@/lib/config";

const BACKEND_URL = config.backend.brainMcp;

function validateTaskParam(task: string | null): string {
  if (!task) return "";
  if (task.length > 1000) return task.slice(0, 1000);
  return task.replace(/[<>]/g, "");
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const task = validateTaskParam(searchParams.get("task"));
    const contextType = searchParams.get("contextType") || "all";
    
    if (!["all", "semantic", "episodic", "session"].includes(contextType)) {
      return NextResponse.json({ error: "Invalid contextType" }, { status: 400 });
    }
    
    const r = await fetch(
      `${BACKEND_URL}/memory_context?task=${encodeURIComponent(task)}&contextType=${contextType}`,
      { signal: AbortSignal.timeout(10000) }
    );
    
    if (!r.ok) {
      return NextResponse.json({ error: `Backend error: ${r.status}` }, { status: r.status });
    }
    
    const data = await r.json();
    return NextResponse.json(data);
  } catch (e: unknown) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Internal error" },
      { status: 500 }
    );
  }
}