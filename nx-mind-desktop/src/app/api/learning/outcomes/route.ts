import { NextRequest, NextResponse } from "next/server";
import { config } from "@/lib/config";

const BACKEND_URL = config.backend.httpGateway;

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const agent = searchParams.get("agent");
  const taskType = searchParams.get("task_type");
  const limit = searchParams.get("limit") || "100";
  
  try {
    let url = `${BACKEND_URL}/api/routing/outcomes?limit=${limit}`;
    if (agent) url += `&agent=${agent}`;
    if (taskType) url += `&task_type=${taskType}`;
    
    const res = await fetch(url, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) {
      return NextResponse.json({ status: "error", outcomes: [] }, { status: 502 });
    }
    
    const data = await res.json();
    return NextResponse.json({ 
      status: "ok", 
      outcomes: data.data || [] 
    });
  } catch (e: any) {
    return NextResponse.json({ status: "error", outcomes: [], message: e.message }, { status: 502 });
  }
}