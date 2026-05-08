export const dynamic = 'force-static';
import { NextResponse } from "next/server";
import { config } from "@/lib/config";

const BACKEND_URL = config.backend.brainMcp;

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const q = searchParams.get("q") || "";
  const limit = parseInt(searchParams.get("limit") || "10", 10);
  
  try {
    const resp = await fetch(`${BACKEND_URL}/memory_search?query=${encodeURIComponent(q)}&limit=${limit}`, {
      signal: AbortSignal.timeout(5000)
    });
    if (resp.ok) {
      const data = await resp.json();
      return NextResponse.json({
        results: data.results || [],
        query: q,
        total: data.total || 0,
        unified: true,
        source: "brain_mcp"
      });
    }
  } catch (e) {
    console.error("Memory search failed:", e);
  }
  
  return NextResponse.json({
    results: [],
    query: q,
    total: 0,
    unified: true,
    source: "fallback"
  });
}
