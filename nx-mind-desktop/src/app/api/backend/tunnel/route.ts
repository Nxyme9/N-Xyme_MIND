import { NextRequest, NextResponse } from "next/server";
import { config } from "@/lib/config";

const BACKEND_URL = config.backend.httpGateway;

export async function GET(request: NextRequest) {
  try {
    const res = await fetch(`${BACKEND_URL}/tunnel_status`, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) {
      return NextResponse.json({ fallback_mode: false, error: "Backend unavailable" }, { status: 502 });
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (e: any) {
    return NextResponse.json({ fallback_mode: false, error: e.message }, { status: 502 });
  }
}