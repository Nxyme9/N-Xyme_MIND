export const dynamic = 'force-static';
import { NextRequest, NextResponse } from "next/server";
import { config } from "@/lib/config";

const BACKEND_URL = config.backend.httpGateway;

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/orchestration_workflows`, {
      signal: AbortSignal.timeout(5000),
    });
    if (response.ok) {
      const data = await response.json();
      return NextResponse.json({ status: "ok", workflows: data.workflows || [] });
    }
  } catch (e) {
    console.error("Workflows fetch failed:", e);
  }
  return NextResponse.json({ status: "ok", workflows: [] });
}