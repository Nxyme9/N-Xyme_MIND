import { NextResponse } from "next/server";
import { config } from "@/lib/config";

const BACKEND_URL = config.backend.httpGateway;

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/tools_list`, {
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) {
      return NextResponse.json({ 
        status: "error", 
        error: `Backend returned ${res.status}`,
        backendUrl: BACKEND_URL 
      }, { status: 502 });
    }
    const data = await res.json();
    return NextResponse.json({ status: "ok", data: data.agents || [], raw: data });
  } catch (e: any) {
    return NextResponse.json({ 
      status: "error", 
      error: e.message || "Connection failed",
      backendUrl: BACKEND_URL 
    }, { status: 502 });
  }
}