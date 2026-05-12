"use client";

import { useEffect } from "react";
import { useWebSocket } from "./useWebSocket";
import { useAgentStore, type Agent } from "@/stores/useAgentStore";
import { useTaskStore, type Task } from "@/stores/useTaskStore";

interface AgentStreamMessage {
  type: "agent_update" | "task_update" | "status";
  payload: {
    agentId?: string;
    status?: Agent["status"];
    currentTask?: string;
    task?: Partial<Task> & { priority?: Task["priority"] };
    message?: string;
  };
}

function getWebSocketUrl(): string {
  if (typeof window === "undefined") return "ws://localhost:8000/ws/stream";
  return `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws/stream`;
}

export function useAgentStream() {
  const updateAgent = useAgentStore((state) => state.updateAgent);
  const addTask = useTaskStore((state) => state.addTask);
  const updateTask = useTaskStore((state) => state.updateTask);

  const handleMessage = (data: unknown) => {
    const message = data as AgentStreamMessage;

    switch (message.type) {
      case "agent_update":
        if (message.payload.agentId) {
          updateAgent(message.payload.agentId, {
            status: message.payload.status,
            currentTask: message.payload.currentTask,
            lastActive: new Date(),
          });
        }
        break;

      case "task_update":
        if (message.payload.task) {
          if (message.payload.task.id) {
            updateTask(message.payload.task.id, message.payload.task);
          } else if (message.payload.task.description) {
            addTask({
              id: crypto.randomUUID(),
              description: message.payload.task.description,
              status: message.payload.task.status || "pending",
              priority: message.payload.task.priority || "medium",
              createdAt: new Date(),
            });
          }
        }
        break;

      case "status":
        // Handle general status messages
        break;

      default:
        console.warn("Unknown message type:", message);
    }
  };

  const { isConnected, lastMessage, sendMessage, disconnect } = useWebSocket({
    url: getWebSocketUrl(),
    onMessage: handleMessage,
    onConnect: () => {},
    onDisconnect: () => {},
    reconnectAttempts: 5,
    reconnectInterval: 3000,
  });

  const sendAgentCommand = (agentId: string, command: string, payload?: unknown) => {
    sendMessage({
      type: "command",
      agentId,
      command,
      payload,
    });
  };

  return {
    isConnected,
    lastMessage,
    sendAgentCommand,
    disconnect,
  };
}