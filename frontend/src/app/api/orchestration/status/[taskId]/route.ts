export const dynamic = 'force-static';
import { NextRequest, NextResponse } from "next/server";
import { config } from "@/lib/config";

const BACKEND_URL = config.backend.httpGateway;

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ taskId: string }> }
) {
  try {
    const { taskId } = await params;
    const res = await fetch(`${BACKEND_URL}/orchestration_task_status/${taskId}`, {
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) {
      return NextResponse.json({ status: "error", data: undefined }, { status: 502 });
    }
    const data = await res.json();
    return NextResponse.json({ status: "ok", data });
  } catch (e: any) {
    return NextResponse.json({ status: "error", data: undefined }, { status: 502 });
  }
}