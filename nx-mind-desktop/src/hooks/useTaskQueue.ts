import { useState, useEffect } from "react";

interface QueueMetrics {
  pending: number;
  running: number;
  completed: number;
}

export function useTaskQueue() {
  const [metrics, setMetrics] = useState<QueueMetrics>({ pending: 0, running: 0, completed: 0 });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchQueue() {
      try {
        const res = await fetch("/api/orchestration/queue");
        if (res.ok) {
          const data = await res.json();
          setMetrics(data);
        }
      } catch {}
      setIsLoading(false);
    }
    fetchQueue();
    const interval = setInterval(fetchQueue, 10000);
    return () => clearInterval(interval);
  }, []);

  return { metrics, isLoading };
}