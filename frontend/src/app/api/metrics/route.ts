export const dynamic = 'force-static';
import { NextRequest, NextResponse } from "next/server";
import { config } from "@/lib/config";

const BACKEND_URL = config.backend.httpGateway;

interface MetricFamily {
  name: string;
  help: string;
  type: string;
  values: { labels: Record<string, string>; value: number }[];
}

async function fetchBackendMetrics(): Promise<string> {
  const metrics: string[] = [];
  
  try {
    const [learningRes, queueRes, mcpRes] = await Promise.allSettled([
      fetch(`${BACKEND_URL}/api/routing/status`, { signal: AbortSignal.timeout(3000) }),
      fetch(`${BACKEND_URL}/orchestration_queue_stats`, { signal: AbortSignal.timeout(3000) }),
      fetch(`${BACKEND_URL}/mcp_stats`, { signal: AbortSignal.timeout(3000) }),
    ]);

    if (learningRes.status === "fulfilled" && learningRes.value.ok) {
      const data = await learningRes.value.json();
      if (data.totalOutcomes) {
        metrics.push(`# HELP learning_total_outcomes Total number of learning outcomes tracked`);
        metrics.push(`# TYPE learning_total_outcomes counter`);
        metrics.push(`learning_total_outcomes ${data.totalOutcomes}`);
      }
      if (data.successRate) {
        metrics.push(`# HELP learning_success_rate Current success rate of delegated tasks`);
        metrics.push(`# TYPE learning_success_rate gauge`);
        metrics.push(`learning_success_rate ${data.successRate}`);
      }
      if (data.abTests) {
        const activeTests = Object.values(data.abTests).filter((t: any) => t.is_active).length;
        metrics.push(`# HELP learning_ab_tests_active Number of active A/B tests`);
        metrics.push(`# TYPE learning_ab_tests_active gauge`);
        metrics.push(`learning_ab_tests_active ${activeTests}`);
      }
    }

    if (queueRes.status === "fulfilled" && queueRes.value.ok) {
      const data = await queueRes.value.json();
      metrics.push(`# HELP orchestration_queue_pending Number of pending tasks in queue`);
      metrics.push(`# TYPE orchestration_queue_pending gauge`);
      metrics.push(`orchestration_queue_pending ${data.pending || 0}`);
      metrics.push(`orchestration_queue_running ${data.running || 0}`);
      metrics.push(`orchestration_queue_completed ${data.completed || 0}`);
    }
  } catch (e) {
      console.error("Metrics fetch failed:", e);
    }

  return metrics.join("\n") || "# No metrics available";
}

export async function GET(request: NextRequest): Promise<NextResponse> {
  const format = request.nextUrl.searchParams.get("format");
  
  if (format === "text") {
    const metrics = await fetchBackendMetrics();
    return new NextResponse(metrics, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
      },
    });
  }

  return NextResponse.json({
    endpoints: {
      text: "/api/metrics?format=text",
      json: "/api/metrics",
    },
    timestamp: new Date().toISOString(),
  });
}