export const dynamic = 'force-static';
import { NextRequest, NextResponse } from "next/server";
import { readFile, writeFile, mkdir } from "fs/promises";
import { join } from "path";
import { existsSync } from "fs";

interface ApiKey {
  id: string;
  name: string;
  key: string;
  provider: string;
  createdAt: string;
  permission: "read-only" | "full-access";
  usage?: {
    callsThisMonth: number;
    tokensUsed: number;
    lastUsed: string;
  };
}

interface ApiKeysResponse {
  keys: ApiKey[];
  timestamp: string;
}

const KEYS_FILE = join(process.cwd(), "data", "api-keys.json");

async function loadKeys(): Promise<ApiKey[]> {
  try {
    if (!existsSync(KEYS_FILE)) return [];
    const data = await readFile(KEYS_FILE, "utf-8");
    return JSON.parse(data);
  } catch {
    return [];
  }
}

async function saveKeys(keys: ApiKey[]): Promise<void> {
  const dir = join(process.cwd(), "data");
  if (!existsSync(dir)) await mkdir(dir, { recursive: true });
  await writeFile(KEYS_FILE, JSON.stringify(keys, null, 2));
}

function maskKey(key: string): string {
  if (!key || key.length < 8) return "****";
  return `${key.slice(0, 4)}${"x".repeat(key.length - 8)}${key.slice(-4)}`;
}

export async function GET(): Promise<NextResponse<ApiKeysResponse>> {
  const keys = await loadKeys();
  const maskedKeys = keys.map(k => ({ ...k, key: maskKey(k.key) }));
  
  return NextResponse.json({
    keys: maskedKeys,
    timestamp: new Date().toISOString(),
  });
}

export async function POST(
  request: NextRequest
): Promise<NextResponse<ApiKeysResponse>> {
  try {
    const body = await request.json();
    const { name, key, provider, permission = "full-access" } = body;
    
    if (!name || !key || !provider) {
      return NextResponse.json(
        { keys: [], timestamp: new Date().toISOString() },
        { status: 400 }
      );
    }
    
    const keys = await loadKeys();
    const newKey: ApiKey = {
      id: `${Date.now()}`,
      name,
      key,
      provider,
      createdAt: new Date().toISOString().split("T")[0],
      permission,
    };
    
    keys.push(newKey);
    await saveKeys(keys);
    
    return NextResponse.json({
      keys: keys.map(k => ({ ...k, key: maskKey(k.key) })),
      timestamp: new Date().toISOString(),
    });
  } catch (e: unknown) {
    return NextResponse.json(
      { 
        keys: [], 
        timestamp: new Date().toISOString(),
        error: e instanceof Error ? e.message : "Internal error" 
      },
      { status: 500 }
    );
  }
}