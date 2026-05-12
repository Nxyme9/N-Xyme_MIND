// Simplified auth handler - using NextAuth v5 beta compatible approach
import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const action = url.searchParams.get("action");
  
  if (action === "signin") {
    // Simple credential check - in production use proper auth
    const authHeader = request.headers.get("authorization");
    if (authHeader === "Basic YWRtaW46YWRtaW4=") { // admin:admin base64
      return NextResponse.json({ 
        user: { id: "1", name: "admin", email: "admin@localhost" },
        token: "dev-token"
      });
    }
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  
  return NextResponse.json({ status: "ok" });
}

export async function POST(request: Request) {
  return GET(request);
}
