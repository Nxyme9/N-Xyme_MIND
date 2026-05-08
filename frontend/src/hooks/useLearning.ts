import { useState, useEffect } from "react";

interface LearningStats {
  totalOutcomes?: number;
  successRate?: number;
  avgLatency?: number;
  routingWeights?: Record<string, number>;
  abTests?: Record<string, unknown>;
  agentPerformance?: Record<string, { success: number; total: number; avgLatency: number }>;
  status?: string;
  error?: string;
}

export function useLearningStats() {
  const [stats, setStats] = useState<LearningStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isError, setIsError] = useState(false);

  useEffect(() => {
    async function fetchStats() {
      try {
        const res = await fetch("/api/learning/status");
        if (res.ok) {
          const data = await res.json();
          setStats(data);
          setIsError(false);
        } else {
          setIsError(true);
        }
      } catch {
        setIsError(true);
      }
      setIsLoading(false);
    }
    fetchStats();
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  return { stats, isLoading, isError };
}

export function useLearningOutcomes(limit = 20) {
  const [outcomes, setOutcomes] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchOutcomes() {
      try {
        const res = await fetch(`/api/learning/outcomes?limit=${limit}`);
        if (res.ok) {
          const data = await res.json();
          setOutcomes(data.outcomes || []);
        }
      } catch (e) {
        console.error("Learning stats fetch failed:", e);
      }
      setIsLoading(false);
    }
    fetchOutcomes();
  }, [limit]);

  return { outcomes, isLoading };
}

interface TrendData {
  agent: string;
  success_rate: number;
  total_tasks: number;
  successful: number;
}

export function useLearningTrends(days = 7) {
  const [trends, setTrends] = useState<TrendData[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchTrends() {
      try {
        const res = await fetch(`/api/learning/trends?days=${days}`);
        if (res.ok) {
          const data = await res.json();
          setTrends(data.trends || []);
        }
      } catch (e) {
        console.error("Learning stats fetch failed:", e);
      }
      setIsLoading(false);
    }
    fetchTrends();
    const interval = setInterval(fetchTrends, 60000);
    return () => clearInterval(interval);
  }, [days]);

  return { trends, isLoading };
}

export interface LatencyMetrics {
  latency_by_agent: Array<{
    agent: string;
    task_count: number;
    avg_latency_ms: number;
    min_latency_ms: number;
    max_latency_ms: number;
  }>;
  success_by_agent: Array<{
    agent: string;
    total_tasks: number;
    successful_tasks: number;
    success_rate: number;
    avg_latency_ms: number;
  }>;
  complexity_level: Array<{
    level: number;
    count: number;
    successes: number;
    success_rate: number;
    avg_latency_ms: number;
  }>;
  daily_trend: Array<{
    date: string;
    agent: string;
    tasks: number;
    success_rate: number;
    avg_latency_ms: number;
  }>;
  summary: {
    total_tasks: number;
    avg_latency_ms: number;
    overall_success_rate: string;
    period_days: number;
  };
}

export function useLatencyMetrics(days = 7) {
  const [metrics, setMetrics] = useState<LatencyMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchMetrics() {
      try {
        const res = await fetch(`/api/learning/latency?days=${days}`);
        if (res.ok) {
          const data = await res.json();
          setMetrics(data);
        }
      } catch (e) {
        console.error("Learning stats fetch failed:", e);
      }
      setIsLoading(false);
    }
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 60000);
    return () => clearInterval(interval);
  }, [days]);

  return { metrics, isLoading };
}

export interface Recommendation {
  type: string;
  priority: string;
  message: string;
  action: string;
  icon: string;
  agent?: string;
  level?: string;
}

export interface RecommendationsSummary {
  total_recommendations: number;
  high_priority: number;
  period_days: number;
}

export function useRecommendations(days = 7) {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [summary, setSummary] = useState<RecommendationsSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchRecommendations() {
      try {
        const res = await fetch(`/api/learning/recommendations?days=${days}`);
        if (res.ok) {
          const data = await res.json();
          setRecommendations(data.recommendations || []);
          setSummary(data.summary);
        }
      } catch (e) {
        console.error("Learning stats fetch failed:", e);
      }
      setIsLoading(false);
    }
    fetchRecommendations();
    const interval = setInterval(fetchRecommendations, 60000);
    return () => clearInterval(interval);
  }, [days]);

  return { recommendations, summary, isLoading };
}