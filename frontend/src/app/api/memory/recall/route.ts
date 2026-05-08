export const dynamic = 'force-static';
import { NextRequest, NextResponse } from "next/server";
import { config } from "@/lib/config";

const BACKEND_URL = config.backend.brainMcp;

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const session = searchParams.get("session")?.slice(0, 100) || "";
  const limit = parseInt(searchParams.get("limit") || "10", 10);
  
  try {
    const resp = await fetch(`${BACKEND_URL}/memory_recall?session=${encodeURIComponent(session)}&limit=${limit}`, {
      signal: AbortSignal.timeout(5000)
    });
    if (resp.ok) {
      const data = await resp.json();
      return NextResponse.json({
        sessions: data.sessions || [],
        current_session: session,
        total: data.total || 0,
        source: "brain_mcp"
      });
    }
  } catch (e) {
    console.error("Memory recall failed:", e);
  }
  
  return NextResponse.json({
    sessions: [],
    current_session: session,
    total: 0,
    source: "fallback"
  });
}