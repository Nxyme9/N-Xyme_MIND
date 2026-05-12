import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const q = searchParams.get("q") || "";
  
  try {
    const stats = await fetch("http://localhost:8765/memory_stats").then(r => r.json());
    return NextResponse.json({
      results: [],
      query: q,
      total: stats.file_registry?.file_registry || 0,
      unified: true,
      source: "memory_stats"
    });
  } catch {
    return NextResponse.json({ results: [], query: q, total: 0, unified: true, source: "fallback" });
  }
}
