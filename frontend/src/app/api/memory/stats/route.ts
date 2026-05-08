export const dynamic = 'force-static';
import { NextResponse } from "next/server";
import { config } from "@/lib/config";

const BACKEND_URL = config.backend.httpGateway;

export async function GET() {
  try {
    const r = await fetch(`${BACKEND_URL}/memory_stats`, { signal: AbortSignal.timeout(5000) });
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