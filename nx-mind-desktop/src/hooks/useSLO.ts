import { useState, useEffect } from "react";

interface SLOHealth {
  slo_type?: string;
  current?: number;
  target?: number;
  status?: string;
  healthy?: boolean;
}

export function useSLOHealth() {
  const [health, setHealth] = useState<Record<string, SLOHealth> | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchSLO() {
      try {
        const res = await fetch("/api/orchestration/slo");
        if (res.ok) {
          const data = await res.json();
          setHealth(data.slos || data);
        }
      } catch {}
      setIsLoading(false);
    }
    fetchSLO();
    const interval = setInterval(fetchSLO, 60000);
    return () => clearInterval(interval);
  }, []);

  const overallHealthy = health 
    ? Object.values(health).every(slo => slo.healthy !== false)
    : true;

  return { health, isLoading, overallHealthy };
}