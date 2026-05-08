"use client";

import { useEffect, useRef, useState, useCallback } from "react";

interface UseWebSocketOptions {
  url: string;
  onMessage?: (data: unknown) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  reconnectAttempts?: number;
  reconnectInterval?: number;
}

export function useWebSocket({
  url,
  onMessage,
  onConnect,
  onDisconnect,
  reconnectAttempts = 5,
  reconnectInterval = 3000,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<unknown>(null);
  const reconnectCountRef = useRef(0);
  const reconnectAttemptsRef = useRef(reconnectAttempts);
  const reconnectIntervalRef = useRef(reconnectInterval);
  const connectRef = useRef<() => void>(() => {}); // Store connect function
  
  // Store callbacks in refs to avoid stale closures
  const onMessageRef = useRef(onMessage);
  const onConnectRef = useRef(onConnect);
  const onDisconnectRef = useRef(onDisconnect);
  
  // Update refs when callbacks change
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);
  
  useEffect(() => {
    onConnectRef.current = onConnect;
  }, [onConnect]);
  
  useEffect(() => {
    onDisconnectRef.current = onDisconnect;
  }, [onDisconnect]);
  
  useEffect(() => {
    reconnectAttemptsRef.current = reconnectAttempts;
  }, [reconnectAttempts]);
  
  useEffect(() => {
    reconnectIntervalRef.current = reconnectInterval;
  }, [reconnectInterval]);

  const connect = useCallback(() => {
    const ws = new WebSocket(url);

    ws.onopen = () => {
      setIsConnected(true);
      reconnectCountRef.current = 0;
      onConnectRef.current?.();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLastMessage(data);
        onMessageRef.current?.(data);
      } catch (e) {
        console.error("Failed to parse WebSocket message:", e);
        setLastMessage(event.data);
        onMessageRef.current?.(event.data);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      onDisconnectRef.current?.();

      // Reconnection logic - use refs to access current values
      if (reconnectCountRef.current < reconnectAttemptsRef.current) {
        reconnectCountRef.current += 1;
        setTimeout(connectRef.current, reconnectIntervalRef.current);
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    wsRef.current = ws;
  }, [url]);

  // Store connect in ref so it can be called from onclose before declaration
  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  const sendMessage = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  const disconnect = useCallback(() => {
    reconnectCountRef.current = reconnectAttemptsRef.current; // Prevent reconnect
    wsRef.current?.close();
  }, []);

  useEffect(() => {
    connect();
    return () => {
      reconnectCountRef.current = reconnectAttemptsRef.current;
      wsRef.current?.close();
    };
  }, [connect]);

  return { isConnected, lastMessage, sendMessage, disconnect };
}