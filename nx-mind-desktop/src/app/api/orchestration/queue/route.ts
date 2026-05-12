import { NextRequest, NextResponse } from "next/server";
import { config } from "@/lib/config";

const BACKEND_URL = config.backend.httpGateway;

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/orchestration_tasks_summary`, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) {
      return NextResponse.json({ pending: 0, running: 0, completed: 0 }, { status: 502 });
    }
    const data = await res.json();
    return NextResponse.json({ 
      pending: data.pending || data.queue_length || 0,
      running: data.running || 0,
      completed: data.completed || 0 
    });
  } catch {
    return NextResponse.json({ pending: 0, running: 0, completed: 0 });
  }
}