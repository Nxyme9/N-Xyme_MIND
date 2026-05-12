import { NextRequest, NextResponse } from "next/server";
import { config } from "@/lib/config";

const BACKEND_URL = config.backend.httpGateway;

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const qParam = searchParams.get("query") || searchParams.get("q");
    const finalQ = (!qParam || qParam.trim() === "") ? "*" : qParam;
    const limitParam = searchParams.get("limit");
    const safeQ = finalQ.slice(0, 500);
    const safeLimit = Math.min(Math.max(parseInt(limitParam || "50") || 50, 1), 100);
    
    const r = await fetch(
      `${BACKEND_URL}/memory_get`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: safeQ, limit: safeLimit }),
        signal: AbortSignal.timeout(10000)
      }
    );
    
    if (!r.ok) {
      return NextResponse.json({ error: `Backend error: ${r.status}`, results: [] }, { status: r.status });
    }
    
    const data = await r.json();
    return NextResponse.json(data);
  } catch (e: unknown) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Internal error", results: [] },
      { status: 500 }
    );
  }
}