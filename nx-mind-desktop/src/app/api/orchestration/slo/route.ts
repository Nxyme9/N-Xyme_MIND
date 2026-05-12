import { NextRequest, NextResponse } from "next/server";
import { config } from "@/lib/config";

const BACKEND_URL = config.backend.httpGateway;

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/orchestration/slo/health`, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) {
      return NextResponse.json({ status: "error", message: "Backend unavailable" }, { status: 502 });
    }
    const data = await res.json();
    return NextResponse.json({ status: "ok", ...data });
  } catch (e: any) {
    return NextResponse.json({ status: "error", message: e.message }, { status: 502 });
  }
}