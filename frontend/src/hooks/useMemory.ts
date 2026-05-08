"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { useEffect } from "react";

const API_BASE = ""; // Use relative URLs - frontend proxies to backend

// Types
interface SemanticMemory {
  id: string;
  content: string;
  type: string;
  trust: number;
}

interface EpisodicMemory {
  id: string;
  content: string;
  timestamp: string;
  trust: number;
}

interface MemorySearchResponse {
  status?: string;
  results?: Array<{ id: string; content: string; type?: string; source?: string; score?: number }>;
  data?: {
    results?: Array<{ id: string; content: string; type?: string; source?: string; score?: number }>;
    [key: string]: unknown;
  };
  error?: string;
}

interface MemoryStatsResponse {
  status: string;
  file_registry?: Record<string, number>;
  learning_events?: number;
  learner?: { status: string };
  [key: string]: unknown;
}

interface MemoryRecallResponse {
  status: string;
  data?: {
    sessions?: Array<{ session_id: string; messages?: unknown[] }>;
    [key: string]: unknown;
  };
}

interface MemoryContextResponse {
  status: string;
  data?: {
    context?: string;
    related?: string[];
    [key: string]: unknown;
  };
}

interface MemoryWriteRequest {
  content: string;
  kind?: string;
  scope?: string;
}

interface MemoryWriteResponse {
  status: string;
  data?: { memory_id?: string };
}

// Search memories
async function searchMemories(
  query: string,
  limit: number = 10,
  strict: boolean = false
): Promise<MemorySearchResponse> {
  try {
    const params = new URLSearchParams({ query, limit: String(limit) });
    if (strict) params.append("strict", "true");
    const response = await fetch(`${API_BASE}/api/memory/search?${params}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  } catch (error) {
    console.error("Failed to search memories:", error);
    return { status: "error", data: { results: [] } };
  }
}

// Get memory stats
async function fetchMemoryStats(): Promise<MemoryStatsResponse> {
  try {
    const response = await fetch(`${API_BASE}/api/memory/stats`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  } catch (error) {
    console.error("Failed to fetch memory stats:", error);
    return { status: "error", data: { total_memories: 0 } };
  }
}

// Recall session context
async function recallSession(sessionId?: string, limit: number = 50): Promise<MemoryRecallResponse> {
  try {
    const params = new URLSearchParams({ limit: String(limit) });
    if (sessionId) params.append("session_id", sessionId);
    const response = await fetch(`${API_BASE}/api/memory/recall?${params}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  } catch (error) {
    console.error("Failed to recall session:", error);
    return { status: "error", data: { sessions: [] } };
  }
}

// Find context for a task
async function findContext(task: string, contextType: string = "all"): Promise<MemoryContextResponse> {
  try {
    const params = new URLSearchParams({ task, context_type: contextType });
    const response = await fetch(`${API_BASE}/api/memory/context?${params}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  } catch (error) {
    console.error("Failed to find context:", error);
    return { status: "error", data: {} };
  }
}

// Write to memory
async function writeMemory(request: MemoryWriteRequest): Promise<MemoryWriteResponse> {
  try {
    const response = await fetch(`${API_BASE}/api/memory/write`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  } catch (error) {
    console.error("Failed to write memory:", error);
    return { status: "error" };
  }
}

// Unified search across all memory sources
async function unifiedSearch(query: string, limit: number = 10): Promise<MemorySearchResponse> {
  try {
    const params = new URLSearchParams({ query, limit: String(limit) });
    const response = await fetch(`${API_BASE}/api/memory/unified/search?${params}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  } catch (error) {
    console.error("Failed to unified search:", error);
    return { status: "error", data: { results: [] } };
  }
}

export function useMemorySearch(query: string, limit: number = 10) {
  const query_ = useQuery({
    queryKey: ["memorySearch", query],
    queryFn: () => searchMemories(query, limit),
    enabled: true, // Always enabled - allows searching with empty query to get all memories
    staleTime: 30000,
  });

  return {
    results: query_.data?.results || [],
    isLoading: query_.isLoading,
    isError: query_.isError,
    error: query_.error,
    refetch: query_.refetch,
  };
}

export function useMemoryStats() {
  const query = useQuery({
    queryKey: ["memoryStats"],
    queryFn: fetchMemoryStats,
    refetchInterval: 30000, // 30s
  });

  return {
    stats: query.data,
    totalMemories: query.data?.file_registry?.file_registry || 0,
    storeStats: query.data?.file_registry,
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: query.refetch,
  };
}

export function useMemoryRecall(sessionId?: string, limit: number = 50) {
  const query = useQuery({
    queryKey: ["memoryRecall", sessionId],
    queryFn: () => recallSession(sessionId, limit),
    enabled: !!sessionId,
  });

  return {
    sessions: query.data?.data?.sessions || [],
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: query.refetch,
  };
}

export function useMemoryContext(task: string, contextType: string = "all") {
  const query = useQuery({
    queryKey: ["memoryContext", task, contextType],
    queryFn: () => findContext(task, contextType),
    enabled: task.length > 0,
    staleTime: 60000, // Context is less dynamic
  });

  return {
    context: query.data?.data?.context,
    related: query.data?.data?.related || [],
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: query.refetch,
  };
}

export function useMemoryWrite() {
  return useMutation({
    mutationFn: (request: MemoryWriteRequest) => writeMemory(request),
  });
}

export function useUnifiedMemorySearch(query: string, limit: number = 10) {
  const query_ = useQuery({
    queryKey: ["unifiedMemorySearch", query],
    queryFn: () => unifiedSearch(query, limit),
    enabled: query.length > 0,
    staleTime: 30000,
  });

  return {
    results: query_.data?.data?.results || [],
    isLoading: query_.isLoading,
    isError: query_.isError,
    refetch: query_.refetch,
  };
}