"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { useState, useEffect, useRef, useCallback } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

// Types
interface ChatModel {
  name: string;
  provider?: string;
  size?: number;
  modified?: string;
}

interface ChatModelsResponse {
  status: string;
  models?: string[];
  ollama?: string[];
  providers?: Record<string, string[]>;
  stats?: Record<string, unknown>;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  thinking?: string;
  tools?: string[];
  model?: string;
  error?: string;
  reactions?: string[];
}

interface ChatCompletionRequest {
  model: string;
  messages: Array<{ role: string; content: string }>;
  stream?: boolean;
  temperature?: number;
  max_tokens?: number;
}

interface ChatCompletionResponse {
  id?: string;
  choices?: Array<{ message: { content: string }; finish_reason: string }>;
  [key: string]: unknown;
}

// Fetch available models
async function fetchModels(): Promise<ChatModelsResponse> {
  try {
    const response = await fetch(`${API_BASE}/api/chat/models`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  } catch (error) {
    console.error("Failed to fetch models:", error);
    return { status: "error", models: [] };
  }
}

// Send chat completion request
async function sendChatCompletion(request: ChatCompletionRequest): Promise<ChatCompletionResponse> {
  try {
    const response = await fetch(`${API_BASE}/api/chat/completions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  } catch (error) {
    console.error("Failed to send chat completion:", error);
    throw error;
  }
}

// WebSocket connection for streaming
function createWebSocket(onMessage: (data: string) => void, onError?: (error: Event) => void) {
  if (typeof window === "undefined") return null;
  
  try {
    const ws = new WebSocket(`${WS_BASE}/ws/stream`);
    
    ws.onopen = () => {
    };
    
    ws.onmessage = (event) => {
      onMessage(event.data);
    };
    
    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      onError?.(error);
    };
    
    ws.onclose = () => {
    };
    
    return ws;
  } catch (error) {
    console.error("Failed to create WebSocket:", error);
    return null;
  }
}

export function useChatModels() {
  const query = useQuery({
    queryKey: ["chatModels"],
    queryFn: fetchModels,
    refetchInterval: 60000, // 1 minute - models don't change often
    staleTime: 30000,
  });

  return {
    models: query.data?.models || [],
    ollamaModels: query.data?.ollama || [],
    providers: query.data?.providers || {},
    stats: query.data?.stats,
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: query.refetch,
  };
}

interface UseChatOptions {
  initialModel?: string;
  onThinking?: (thinking: string) => void;
  onToolCall?: (tool: string) => void;
}

export function useChat(options: UseChatOptions = {}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentModel, setCurrentModel] = useState(options.initialModel || "minimax-m2.5-free");
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Scroll to bottom when messages change
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Add initial system message
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([
        {
          id: "system",
          role: "assistant",
          content: "Hello! I'm Sisyphus, your AI coding assistant. How can I help you today?",
          timestamp: new Date(),
        },
      ]);
    }
  }, []);

  // Send message
  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isStreaming) return;

    // Add user message
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsStreaming(true);
    setError(null);

    // Create assistant message placeholder
    const assistantMessageId = (Date.now() + 1).toString();
    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
      timestamp: new Date(),
      thinking: "Thinking...",
      model: currentModel,
    };
    setMessages((prev) => [...prev, assistantMessage]);

    try {
      // Call API
      const response = await sendChatCompletion({
        model: currentModel,
        messages: messages
          .filter((m) => m.role !== "system")
          .map((m) => ({ role: m.role, content: m.content })),
      });

      // Update assistant message with response
      const assistantContent =
        response.choices?.[0]?.message?.content || "No response received";
      
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMessageId
            ? { ...m, content: assistantContent, thinking: undefined }
            : m
        )
      );
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to get response";
      setError(errorMessage);
      
      // Update assistant message with error
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMessageId
            ? { ...m, content: "", error: errorMessage, thinking: undefined }
            : m
        )
      );
    } finally {
      setIsStreaming(false);
    }
  }, [currentModel, isStreaming, messages]);

  // Set model
  const setModel = useCallback((model: string) => {
    setCurrentModel(model);
  }, []);

  // Clear messages
  const clearMessages = useCallback(() => {
    setMessages([
      {
        id: "system",
        role: "assistant",
        content: "Hello! I'm Sisyphus, your AI coding assistant. How can I help you today?",
        timestamp: new Date(),
      },
    ]);
    setError(null);
  }, []);

  // Delete a message by id
  const deleteMessage = useCallback((id: string) => {
    setMessages((prev) => prev.filter((m) => m.id !== id));
  }, []);

  // Update message reactions
  const updateMessageReactions = useCallback((id: string, reactions: string[]) => {
    setMessages((prev) =>
      prev.map((m) =>
        m.id === id ? { ...m, reactions } : m
      )
    );
  }, []);

  // Update message content (for edits)
  const updateMessage = useCallback((id: string, content: string) => {
    setMessages((prev) =>
      prev.map((m) =>
        m.id === id ? { ...m, content } : m
      )
    );
  }, []);

  // Stop streaming
  const stopStreaming = useCallback(() => {
    setIsStreaming(false);
  }, []);

  // Regenerate a response for a user message (re-send and get new response)
  const regenerateResponse = useCallback(async (userMessageContent: string) => {
    if (isStreaming) return;
    
    // Remove the last assistant message if exists
    setMessages((prev) => {
      const lastIndex = prev.length - 1;
      if (lastIndex >= 0 && prev[lastIndex].role === "assistant") {
        return prev.slice(0, -1);
      }
      return prev;
    });
    
    // Re-send the user message
    await sendMessage(userMessageContent);
  }, [isStreaming, sendMessage]);

  return {
    messages,
    isStreaming,
    currentModel,
    error,
    sendMessage,
    setModel,
    clearMessages,
    deleteMessage,
    updateMessageReactions,
    updateMessage,
    stopStreaming,
    regenerateResponse,
    messagesEndRef,
  };
}

// WebSocket hook for real-time updates
export function useChatStream() {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = createWebSocket(
      (data) => setLastMessage(data),
      () => setIsConnected(false)
    );
    
    if (ws) {
      wsRef.current = ws;
      setIsConnected(true);
    }
  }, []);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
      setIsConnected(false);
    }
  }, []);

  const sendMessage = useCallback((message: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(message);
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return {
    isConnected,
    lastMessage,
    connect,
    disconnect,
    sendMessage,
  };
}