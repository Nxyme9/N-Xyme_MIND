"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useAgentStore, type Agent } from "@/stores/useAgentStore";
import { useTaskStore, type Task } from "@/stores/useTaskStore";

interface AgentStatusResponse {
  agents: Agent[];
  tasks: Task[];
  timestamp: string;
}

async function fetchAgentStatus(): Promise<AgentStatusResponse> {
  const response = await fetch("/api/agents/status");
  if (!response.ok) {
    throw new Error("Failed to fetch agent status");
  }
  return response.json();
}

export function useAgentPolling({
  enabled = true,
  refetchInterval = 5000,
}: {
  enabled?: boolean;
  refetchInterval?: number;
} = {}) {
  const queryClient = useQueryClient();
  const setAgents = useAgentStore((state) => state.setAgents);

  const query = useQuery({
    queryKey: ["agentStatus"],
    queryFn: fetchAgentStatus,
    enabled,
    refetchInterval,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
    staleTime: 2000,
  });

  // Update store when query data changes
  useEffect(() => {
    if (query.data) {
      setAgents(query.data.agents);
    }
  }, [query.data, setAgents]);

  const refetch = () => {
    queryClient.invalidateQueries({ queryKey: ["agentStatus"] });
  };

  // Derive isPolling from query state directly
  const isPolling = query.isFetching;

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    isPolling,
    refetch,
    lastUpdated: query.dataUpdatedAt ? new Date(query.dataUpdatedAt) : null,
  };
}

// Hook that combines WebSocket with polling fallback
export function useAgentRealTime(options?: {
  wsEnabled?: boolean;
  pollEnabled?: boolean;
  pollInterval?: number;
}) {
  const {
    wsEnabled = true,
    pollEnabled = true,
    pollInterval = 5000,
  } = options || {};

  const [useWebSocket, setUseWebSocket] = useState(wsEnabled);

  // Dynamic import of useAgentStream only on client
  const [AgentStreamHook, setAgentStreamHook] = useState<typeof import("./useAgentStream").useAgentStream | null>(null);

  useEffect(() => {
    import("./useAgentStream").then((module) => {
      setAgentStreamHook(() => module.useAgentStream);
    });
  }, []);

  const wsResult = AgentStreamHook
    ? (() => {
        try {
          return AgentStreamHook();
        } catch {
          return { isConnected: false, sendAgentCommand: undefined };
        }
      })()
    : { isConnected: false, sendAgentCommand: undefined };

  const pollResult = useAgentPolling({
    enabled: pollEnabled && !wsResult.isConnected,
    refetchInterval: pollInterval,
  });

  // Prefer WebSocket if connected, otherwise use polling
  const isConnected = wsResult.isConnected || (pollResult.data !== undefined);

  return {
    isConnected,
    isWebSocketConnected: wsResult.isConnected,
    isPolling: pollResult.isPolling,
    lastUpdated: pollResult.lastUpdated,
    refetch: pollResult.refetch,
    sendMessage: wsResult.sendAgentCommand,
  };
}