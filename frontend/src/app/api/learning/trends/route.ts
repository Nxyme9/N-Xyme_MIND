export const dynamic = 'force-static';
import { NextRequest, NextResponse } from "next/server";
import { config } from "@/lib/config";

const BACKEND_URL = config.backend.httpGateway;

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const days = searchParams.get("days") || "7";
  
  try {
    const res = await fetch(`${BACKEND_URL}/api/routing/outcomes?limit=1000`, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) {
      return NextResponse.json({ status: "error", trends: [] }, { status: 502 });
    }
    
    const data = await res.json();
    const outcomes = data.data || [];
    
    const now = Date.now();
    const dayMs = 24 * 60 * 60 * 1000;
    const cutoff = now - (parseInt(days) * dayMs);
    
    const filtered = outcomes.filter((o: any) => {
      const ts = o.timestamp || o.created_at;
      return ts && new Date(ts).getTime() > cutoff;
    });
    
    const byAgent: Record<string, { success: number; total: number }> = {};
    for (const o of filtered) {
      const agent = o.agent || o.delegated_to || "unknown";
      if (!byAgent[agent]) {
        byAgent[agent] = { success: 0, total: 0 };
      }
      byAgent[agent].total += 1;
      if (o.success) {
        byAgent[agent].success += 1;
      }
    }
    
    const trends = Object.entries(byAgent).map(([agent, stats]) => ({
      agent,
      success_rate: Math.round((stats.success / stats.total) * 100),
      total_tasks: stats.total,
      successful: stats.success,
    })).sort((a, b) => b.total_tasks - a.total_tasks);
    
    return NextResponse.json({ 
      status: "ok", 
      trends,
      period_days: parseInt(days),
    });
  } catch (e: any) {
    return NextResponse.json({ status: "error", trends: [], message: e.message }, { status: 502 });
  }
}