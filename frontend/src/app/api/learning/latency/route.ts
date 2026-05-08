export const dynamic = 'force-static';
import { NextRequest, NextResponse } from "next/server";
import sqlite3, { Database } from "better-sqlite3";
import { join } from "path";

const DB_PATH = join(process.cwd(), ".sisyphus", "outcomes.db");

interface LatencyRow {
  agent: string;
  task_count: number;
  avg_latency_ms: number;
  min_latency_ms: number;
  max_latency_ms: number;
}

interface SuccessRow {
  agent: string;
  total_tasks: number;
  successful_tasks: number;
  success_rate: number;
  avg_latency_ms: number;
}

interface LevelRow {
  level: number;
  count: number;
  successes: number;
  success_rate: number;
  avg_latency_ms: number;
}

interface TrendRow {
  date: string;
  agent: string;
  tasks: number;
  success_rate: number;
  avg_latency_ms: number;
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const days = parseInt(searchParams.get("days") || "7");
  const cutoff = Math.floor(Date.now() / 1000) - days * 24 * 60 * 60;

  try {
    const db: Database = sqlite3(DB_PATH);
    db.pragma("journal_mode = WAL");

    const latencyStats = db.prepare(`
      SELECT 
        agent,
        COUNT(*) as task_count,
        AVG(latency_ms) as avg_latency_ms,
        MIN(latency_ms) as min_latency_ms,
        MAX(latency_ms) as max_latency_ms,
        AVG(CASE WHEN latency_ms > 0 THEN latency_ms END) as latency_p50,
        (SELECT AVG(latency_ms) FROM outcomes e2 
         WHERE e2.agent = e1.agent AND e2.timestamp > ? 
         ORDER BY e2.latency_ms LIMIT (SELECT COUNT(*) FROM outcomes e3 WHERE e3.agent = e1.agent AND e3.timestamp > ?) / 2) as latency_p95
      FROM outcomes e1
      WHERE timestamp > ?
      GROUP BY agent
      ORDER BY task_count DESC
    `).all(cutoff, cutoff, cutoff) as LatencyRow[];

    const successStats = db.prepare(`
      SELECT 
        agent,
        COUNT(*) as total_tasks,
        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_tasks,
        ROUND(CAST(SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*), 3) as success_rate,
        AVG(latency_ms) as avg_latency_ms
      FROM outcomes
      WHERE timestamp > ?
      GROUP BY agent
      ORDER BY success_rate ASC
    `).all(cutoff) as SuccessRow[];

    const levelDistribution = db.prepare(`
      SELECT 
        level,
        COUNT(*) as count,
        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
        ROUND(CAST(SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*), 3) as success_rate,
        AVG(latency_ms) as avg_latency_ms
      FROM outcomes
      WHERE timestamp > ?
      GROUP BY level
      ORDER BY level ASC
    `).all(cutoff) as LevelRow[];

    const recentTrend = db.prepare(`
      SELECT 
        strftime('%Y-%m-%d', timestamp, 'unixepoch') as date,
        agent,
        COUNT(*) as tasks,
        ROUND(CAST(SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*), 3) as success_rate,
        AVG(latency_ms) as avg_latency_ms
      FROM outcomes
      WHERE timestamp > ?
      GROUP BY date, agent
      ORDER BY date ASC
      LIMIT 100
    `).all(cutoff) as TrendRow[];

    db.close();

    const hotPathSummary = {
      latency_by_agent: latencyStats,
      success_by_agent: successStats,
      complexity_level: levelDistribution,
      daily_trend: recentTrend,
      summary: {
        total_tasks: successStats.reduce((sum, r) => sum + (r.total_tasks || 0), 0),
        avg_latency_ms: Math.round(latencyStats.reduce((sum, r) => sum + (r.avg_latency_ms || 0), 0) / (latencyStats.length || 1)),
        overall_success_rate: successStats.length > 0 
          ? (successStats.reduce((sum, r) => sum + (r.successful_tasks || 0), 0) / successStats.reduce((sum, r) => sum + (r.total_tasks || 0), 0)).toFixed(3)
          : "0",
        period_days: days
      }
    };

    return NextResponse.json(hotPathSummary);
  } catch (error) {
    console.error("[latency] Database error:", error);
    return NextResponse.json({
      error: "Failed to fetch latency metrics",
      latency_by_agent: [],
      success_by_agent: [],
      complexity_level: [],
      daily_trend: [],
      summary: { total_tasks: 0, avg_latency_ms: 0, overall_success_rate: "0", period_days: days }
    }, { status: 200 });
  }
}