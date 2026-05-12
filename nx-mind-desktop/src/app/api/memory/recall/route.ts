import { NextRequest, NextResponse } from "next/server";
import { config } from "@/lib/config";

const BACKEND_URL = config.backend.httpGateway;

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const session = searchParams.get("session")?.slice(0, 100) || "";
    
    const stats = await fetch(`${BACKEND_URL}/memory_stats`, { signal: AbortSignal.timeout(5000) });
    const statsData = await stats.json();
    
    return NextResponse.json({
      sessions: [],
      current_session: session,
      total: statsData.file_registry?.session_archive || 0,
      source: "memory_stats"
    });
  } catch (e: unknown) {
    return NextResponse.json({ 
      sessions: [], 
      current_session: "", 
      total: 0, 
      source: "fallback",
      error: e instanceof Error ? e.message : "Internal error"
    }, { status: 500 });
  }
}