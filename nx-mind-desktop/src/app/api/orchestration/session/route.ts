import { NextRequest, NextResponse } from "next/server";
import { config } from "@/lib/config";

const BACKEND_URL = config.backend.httpGateway;

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/session_pool_stats`, {
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) {
      const errText = await res.text();
      return NextResponse.json({ status: "error", data: {}, backendError: errText }, { status: 502 });
    }
    const data = await res.json();
    return NextResponse.json({ status: "ok", data });
  } catch (e: any) {
    return NextResponse.json({ status: "error", data: {}, message: e.message }, { status: 502 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { user_input } = body;
    
    if (!user_input) {
      return NextResponse.json({ status: "error", message: "user_input required" }, { status: 400 });
    }
    
    const res = await fetch(`${BACKEND_URL}/orchestration_detect_state`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_input }),
      signal: AbortSignal.timeout(5000),
    });
    
    if (!res.ok) {
      const errText = await res.text();
      return NextResponse.json({ status: "error", backendError: errText }, { status: 502 });
    }
    
    const data = await res.json();
    return NextResponse.json({ status: "ok", data });
  } catch (e: any) {
    return NextResponse.json({ status: "error", message: e.message }, { status: 502 });
  }
}