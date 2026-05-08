export const dynamic = 'force-static';
import { NextRequest, NextResponse } from "next/server";
import { config } from "@/lib/config";

const BACKEND_URL = config.backend.httpGateway;

function validateMemoryWriteInput(input: unknown): { content: string; type?: string; scope?: string; tags?: string[] } | null {
  const data = input as Record<string, unknown>;
  if (!data.content || typeof data.content !== "string") return null;
  if (data.content.length > 100000) return null;
  if (data.type && typeof data.type !== "string") return null;
  if (data.scope && typeof data.scope !== "string") return null;
  if (data.tags && !Array.isArray(data.tags)) return null;
  
  return {
    content: data.content as string,
    type: data.type as string | undefined,
    scope: data.scope as string | undefined,
    tags: data.tags as string[] | undefined,
  };
}

export async function POST(request: NextRequest) {
  try {
    let body: unknown;
    try {
      body = await request.json();
    } catch {
      return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
    }
    
    const validated = validateMemoryWriteInput(body);
    if (!validated) {
      return NextResponse.json(
        { error: "Invalid input: content required, max 100KB" },
        { status: 400 }
      );
    }
    
    const r = await fetch(`${BACKEND_URL}/memory_write`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(validated),
    });
    
    if (!r.ok) {
      return NextResponse.json(
        { error: `Backend error: ${r.status}` },
        { status: r.status }
      );
    }
    
    const data = await r.json();
    return NextResponse.json(data);
  } catch (e: unknown) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Internal error" },
      { status: 500 }
    );
  }
}