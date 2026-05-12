"use client";

import { useAgentStore } from "@/stores/useAgentStore";
import { useMCPStore } from "@/stores/useMCPStore";

interface ConnectionStatusProps {
  showLabel?: boolean;
  showDetail?: boolean;
}

export function ConnectionStatus({
  showLabel = true,
  showDetail = false,
}: ConnectionStatusProps) {
  const agents = useAgentStore((state) => state.agents);
  const connections = useMCPStore((state) => state.connections);

  // Determine status based on agents and MCPs
  const hasActiveAgents = agents.some(a => a.status === "working");
  const hasConnectedMCPs = connections.some(c => c.status === "connected");
  
  // Check if we have any agents/MCPs initialized
  const isInitialized = agents.length > 0 || connections.length > 0;
  
  const status = !isInitialized ? "connecting" : (hasActiveAgents || hasConnectedMCPs) ? "connected" : "disconnected";

  const statusConfig = {
    connected: {
      color: "bg-green-500",
      label: "Connected",
      textColor: "text-green-500",
    },
    connecting: {
      color: "bg-yellow-500",
      label: "Connecting...",
      textColor: "text-yellow-500",
    },
    disconnected: {
      color: "bg-red-500",
      label: "Disconnected",
      textColor: "text-red-500",
    },
  };

  const config = statusConfig[status];

  return (
    <div className="flex items-center gap-2">
      <div className={`w-2.5 h-2.5 rounded-full ${config.color}`} />
      {showLabel && (
        <span className={`text-sm font-medium ${config.textColor}`}>
          {config.label}
        </span>
      )}
      {showDetail && status === "disconnected" && (
        <span className="text-xs text-muted-foreground">
          Connection lost - attempting to reconnect
        </span>
      )}
    </div>
  );
}

// Standalone version that doesn't depend on useAgentStream
export function StandaloneConnectionStatus({
  isConnected,
  showLabel = true,
  showDetail = false,
}: {
  isConnected: boolean;
  showLabel?: boolean;
  showDetail?: boolean;
}) {
  const status = isConnected ? "connected" : "disconnected";

  const statusConfig = {
    connected: {
      color: "bg-green-500",
      label: "Connected",
      textColor: "text-green-500",
    },
    connecting: {
      color: "bg-yellow-500",
      label: "Connecting...",
      textColor: "text-yellow-500",
    },
    disconnected: {
      color: "bg-red-500",
      label: "Disconnected",
      textColor: "text-red-500",
    },
  };

  const config = statusConfig[status];

  return (
    <div className="flex items-center gap-2">
      <div className={`w-2.5 h-2.5 rounded-full ${config.color}`} />
      {showLabel && (
        <span className={`text-sm font-medium ${config.textColor}`}>
          {config.label}
        </span>
      )}
      {showDetail && !isConnected && (
        <span className="text-xs text-muted-foreground">
          Connection lost - attempting to reconnect
        </span>
      )}
    </div>
  );
}