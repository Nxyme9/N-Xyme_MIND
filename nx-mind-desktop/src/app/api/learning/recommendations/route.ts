import { NextRequest, NextResponse } from "next/server";
import sqlite3, { Database } from "better-sqlite3";
import { join } from "path";

const DB_PATH = join(process.cwd(), ".sisyphus", "outcomes.db");

interface AgentStatRow {
  agent: string;
  total: number;
  successes: number;
  avg_latency: number;
  avg_tokens: number;
}

interface LevelStatRow {
  level: number;
  total: number;
  successes: number;
  avg_latency: number;
}

interface RecentOutcomeRow {
  agent: string;
  success: number;
  latency_ms: number;
  level: number;
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const days = parseInt(searchParams.get("days") || "7");
  const cutoff = Math.floor(Date.now() / 1000) - days * 24 * 60 * 60;

  try {
    const db: Database = sqlite3(DB_PATH);
    db.pragma("journal_mode = WAL");

    const agentStats = db.prepare(`
      SELECT 
        agent,
        COUNT(*) as total,
        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
        AVG(latency_ms) as avg_latency,
        AVG(tokens_used) as avg_tokens
      FROM outcomes
      WHERE timestamp > ?
      GROUP BY agent
      HAVING total >= 3
      ORDER BY (CAST(successes AS FLOAT) / total) DESC, avg_latency ASC
    `).all(cutoff) as AgentStatRow[];

    const levelStats = db.prepare(`
      SELECT level, COUNT(*) as total, 
             SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
             AVG(latency_ms) as avg_latency
      FROM outcomes
      WHERE timestamp > ?
      GROUP BY level
      ORDER BY level ASC
    `).all(cutoff) as LevelStatRow[];

    const recentOutcome = db.prepare(`
      SELECT agent, success, latency_ms, level
      FROM outcomes
      WHERE timestamp > ?
      ORDER BY timestamp DESC
      LIMIT 20
    `).all(cutoff) as RecentOutcomeRow[];

    db.close();

    const recommendations: Array<{
      type: string;
      priority: string;
      message: string;
      action: string;
      icon: string;
      agent?: string;
      level?: string;
    }> = [];

    for (const agent of agentStats) {
      const successRate = agent.successes / agent.total;
      const avgLatency = agent.avg_latency || 0;

      if (successRate >= 0.9 && avgLatency < 2000) {
        recommendations.push({
          type: "agent_performance",
          priority: "high",
          agent: agent.agent,
          message: `${agent.agent} is performing excellently (${Math.round(successRate * 100)}% success, ${Math.round(avgLatency)}ms avg)`,
          action: "Continue using for similar tasks",
          icon: "✅"
        });
      } else if (successRate < 0.7) {
        recommendations.push({
          type: "agent_performance",
          priority: "medium",
          agent: agent.agent,
          message: `${agent.agent} has low success rate (${Math.round(successRate * 100)}%)`,
          action: "Consider alternative agents for this task type",
          icon: "⚠️"
        });
      }
    }

    for (const level of levelStats) {
      const successRate = level.successes / level.total;
      if (level.total >= 5 && successRate < 0.8) {
        recommendations.push({
          type: "complexity",
          priority: "medium",
          level: `L${level.level}`,
          message: `Complexity L${level.level} has ${Math.round(successRate * 100)}% success rate (${level.total} tasks)`,
          action: `Break down L${level.level} tasks into smaller steps`,
          icon: "📊"
        });
      }
    }

    const recentFails = recentOutcome.filter((o) => !o.success);
    if (recentFails.length > 3) {
      const failAgents = [...new Set(recentFails.map((o) => o.agent))];
      recommendations.push({
        type: "pattern",
        priority: "high",
        message: `Recent failures with: ${failAgents.join(", ")}`,
        action: "Review recent task failures in outcomes",
        icon: "🚨"
      });
    }

    const lowLatencyAgents = agentStats
      .filter((a) => a.avg_latency < 1000)
      .sort((a, b) => a.avg_latency - b.avg_latency);

    if (lowLatencyAgents.length > 0) {
      recommendations.push({
        type: "optimization",
        priority: "low",
        message: `Fastest agents: ${lowLatencyAgents.slice(0, 3).map((a) => `${a.agent}(${Math.round(a.avg_latency)}ms)`).join(", ")}`,
        action: "Use for time-sensitive tasks",
        icon: "⚡"
      });
    }

    recommendations.sort((a, b) => {
      const priorityOrder: Record<string, number> = { high: 0, medium: 1, low: 2 };
      return priorityOrder[a.priority] - priorityOrder[b.priority];
    });

    return NextResponse.json({
      recommendations,
      summary: {
        total_recommendations: recommendations.length,
        high_priority: recommendations.filter((r) => r.priority === "high").length,
        period_days: days,
      },
    });
  } catch (error) {
    console.error("[recommendations] Error:", error);
    return NextResponse.json({
      recommendations: [],
      summary: { total_recommendations: 0, high_priority: 0, period_days: days },
    }, { status: 200 });
  }
}