import { useState, useEffect } from "react";

interface Activity {
  id: string;
  task: string;
  agent: string;
  status: "pending" | "running" | "completed" | "failed";
  timestamp: string;
  duration_ms?: number;
}

export function useSessionActivity() {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchActivity() {
      try {
        const res = await fetch("/api/orchestration/session");
        if (res.ok) {
          const data = await res.json();
          const session = data.data || data;
          const activeTasks = session.active_tasks || [];
          const activitiesList: Activity[] = activeTasks.map((taskId: string, idx: number) => ({
            id: taskId,
            task: session.current_task || `Task ${idx + 1}`,
            agent: "sisyphus",
            status: "running",
            timestamp: new Date().toISOString(),
          }));
          setActivities(activitiesList);
        }
      } catch {}
      setIsLoading(false);
    }
    fetchActivity();
    const interval = setInterval(fetchActivity, 5000);
    return () => clearInterval(interval);
  }, []);

  return { activities, isLoading };
}