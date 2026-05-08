"use client";

import { useState, useEffect } from "react";

interface TunnelBudget {
  tokens_used: number;
  requests: number;
  fallback_mode: boolean;
  alerts: string[];
  timestamp: string;
}

export function useTunnelBudget() {
  const [budget, setBudget] = useState<TunnelBudget | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isError, setIsError] = useState(false);

  useEffect(() => {
    async function fetchBudget() {
      try {
        const res = await fetch("/api/backend/tunnel/budget");
        if (res.ok) {
          const data = await res.json();
          setBudget(data);
          setIsError(false);
        } else {
          setIsError(true);
        }
      } catch {
        setIsError(true);
      }
      setIsLoading(false);
    }
    fetchBudget();
    const interval = setInterval(fetchBudget, 60000);
    return () => clearInterval(interval);
  }, []);

  return { budget, isLoading, isError };
}