import { NextResponse } from "next/server";

const startTime = Date.now();

export async function GET(): Promise<NextResponse> {
  const port = process.env.PORT || process.env.NEXT_PORT || "3000";
  const uptimeSeconds = Math.floor((Date.now() - startTime) / 1000);

  return NextResponse.json(
    {
      status: "ok",
      port: parseInt(port, 10),
      uptime: uptimeSeconds,
      timestamp: new Date().toISOString(),
    },
    {
      status: 200,
      headers: {
        "Cache-Control": "no-cache, no-store, must-revalidate",
      },
    }
  );
}
