"use client";

import { useEffect, useState, useCallback } from "react";
import { useAgentStore, type Agent } from "@/stores/useAgentStore";
import { useMCPStore, type MCPConnection } from "@/stores/useMCPStore";

// Default agents (fallback when backend unavailable)
const DEFAULT_AGENTS: Agent[] = [
  { id: "sisyphus", name: "Sisyphus", status: "idle" },
  { id: "hephaestus", name: "Hephaestus", status: "idle" },
  { id: "oracle", name: "Oracle", status: "idle" },
  { id: "prometheus", name: "Prometheus", status: "idle" },
  { id: "metis", name: "Metis", status: "idle" },
  { id: "momus", name: "Momus", status: "idle" },
  { id: "atlas", name: "Atlas", status: "idle" },
  { id: "explore", name: "Explore", status: "idle" },
  { id: "librarian", name: "Librarian", status: "idle" },
  { id: "plan", name: "Plan", status: "idle" },
  { id: "multimodal_looker", name: "Multimodal Looker", status: "idle" },
];

// Default MCP connections (fallback when backend unavailable)
const DEFAULT_MCPS: MCPConnection[] = [
  { name: "Sequential Thinking", status: "connected" },
  { name: "Memory", status: "connected" },
  { name: "Context7", status: "connected" },
  { name: "Filesystem", status: "connected" },
  { name: "GitHub", status: "connected" },
  { name: "Notion", status: "connected" },
  { name: "Telegram", status: "connected" },
];

interface BackendAgentsResponse {
  agents: Agent[];
  backendAvailable: boolean;
  timestamp: string;
}

interface BackendMCPResponse {
  connections: MCPConnection[];
  backendAvailable: boolean;
  timestamp: string;
}

export function useSystemStatus() {
  const agents = useAgentStore((state) => state.agents);
  const connections = useMCPStore((state) => state.connections);
  const setAgents = useAgentStore((state) => state.setAgents);
  const setConnections = useMCPStore((state) => state.setConnections);

  const [isLoading, setIsLoading] = useState(false);
  const [isError, setIsError] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionLabel, setConnectionLabel] = useState("Checking...");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchAgents = useCallback(async () => {
    try {
      const response = await fetch("/api/backend/agents", {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });

      if (!response.ok) {
        throw new Error(`Agents fetch failed: ${response.status}`);
      }

      const data: BackendAgentsResponse = await response.json();
      setAgents(data.agents);
      return data.backendAvailable;
    } catch (err) {
      console.error("Failed to fetch agents:", err);
      setAgents(DEFAULT_AGENTS);
      return false;
    }
  }, [setAgents]);

  const fetchMCP = useCallback(async () => {
    try {
      const response = await fetch("/api/backend/mcp", {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });

      if (!response.ok) {
        throw new Error(`MCP fetch failed: ${response.status}`);
      }

      const data: BackendMCPResponse = await response.json();
      setConnections(data.connections);
      return data.backendAvailable;
    } catch (err) {
      console.error("Failed to fetch MCP status:", err);
      setConnections(DEFAULT_MCPS);
      return false;
    }
  }, [setConnections]);

  const refetch = useCallback(async () => {
    setIsLoading(true);
    setIsError(false);
    setError(null);

    try {
      const [agentsAvailable, mcpAvailable] = await Promise.all([
        fetchAgents(),
        fetchMCP(),
      ]);

      const backendAvailable = agentsAvailable || mcpAvailable;
      setIsConnected(backendAvailable);
      setConnectionLabel(backendAvailable ? "Connected" : "Using Defaults");
      setLastUpdated(new Date());
    } catch (err) {
      setIsError(true);
      setError(err instanceof Error ? err.message : "Unknown error");
      setIsConnected(false);
      setConnectionLabel("Error");
      // Fallback to defaults
      setAgents(DEFAULT_AGENTS);
      setConnections(DEFAULT_MCPS);
    } finally {
      setIsLoading(false);
    }
  }, [fetchAgents, fetchMCP, setAgents, setConnections]);

  // Initialize with default agents and MCPs if empty, then fetch from backend
  useEffect(() => {
    if (agents.length === 0) {
      setAgents(DEFAULT_AGENTS);
    }
    if (connections.length === 0) {
      setConnections(DEFAULT_MCPS);
    }
    // Fetch from backend
    refetch();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Periodic refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      refetch();
    }, 30000);

    return () => clearInterval(interval);
  }, [refetch]);

  return {
    data: null,
    isLoading,
    isError,
    error,
    isConnected,
    connectionLabel,
    lastUpdated,
    refetch,
  };
}

// Helper hook to get agent status
export function useAgentStatus() {
  const agents = useAgentStore((state) => state.agents);

  return {
    agents,
    activeCount: agents.filter((a) => a.status === "working").length,
    idleCount: agents.filter((a) => a.status === "idle").length,
    errorCount: agents.filter((a) => a.status === "error").length,
  };
}

// Helper hook to get MCP status
export function useMCPStatus() {
  const connections = useMCPStore((state) => state.connections);

  return {
    connections,
    connectedCount: connections.filter((c) => c.status === "connected").length,
    disconnectedCount: connections.filter((c) => c.status === "disconnected").length,
  };
}

export function useMCPDynamic() {
  const setConnections = useMCPStore((state) => state.setConnections);

  const registerMCP = useCallback(async (name: string, type: string, config?: Record<string, string>) => {
    const response = await fetch("/api/backend/mcp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, type, config }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Failed to register MCP");
    }

    const data = await response.json();
    setConnections(data.connections);
    return data.mcp;
  }, [setConnections]);

  const updateMCP = useCallback(async (name: string, status?: string, config?: Record<string, string>) => {
    const response = await fetch("/api/backend/mcp", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, status, config }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Failed to update MCP");
    }

    const data = await response.json();
    setConnections(data.connections);
    return data.mcp;
  }, [setConnections]);

  const deleteMCP = useCallback(async (name: string) => {
    const response = await fetch(`/api/backend/mcp?name=${encodeURIComponent(name)}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Failed to delete MCP");
    }

    const data = await response.json();
    setConnections(data.connections);
    return true;
  }, [setConnections]);

  return { registerMCP, updateMCP, deleteMCP };
}