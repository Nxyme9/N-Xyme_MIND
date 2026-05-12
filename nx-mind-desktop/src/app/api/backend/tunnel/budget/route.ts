import { NextRequest, NextResponse } from "next/server";
import { config } from "@/lib/config";

const BACKEND_URL = config.backend.httpGateway;

export async function GET(request: NextRequest) {
  try {
    const res = await fetch(`${BACKEND_URL}/tunnel_stats`, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) {
      return NextResponse.json({ error: "Backend unavailable" }, { status: 502 });
    }
    const data = await res.json();
    
    const tokens_used = data.tokens_used || 0;
    const budget_threshold = 0.8;
    const alerts: string[] = [];
    
    if (tokens_used > 0) {
      if (tokens_used >= budget_threshold * 100000) {
        alerts.push("Budget at 80%+ - consider switching to faster models");
      }
      if (data.requests_per_minute && data.requests_per_minute > 50) {
        alerts.push("High request rate - consider batching");
      }
    }
    
    return NextResponse.json({
      tokens_used,
      requests: data.requests,
      fallback_mode: data.fallback_mode,
      alerts,
      timestamp: new Date().toISOString(),
    });
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 502 });
  }
}