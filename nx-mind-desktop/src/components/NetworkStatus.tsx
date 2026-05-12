"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";

export function NetworkStatus() {
  const [isOnline, setIsOnline] = useState(true);
  const [wasOnline, setWasOnline] = useState(true);

  useEffect(() => {
    // Set initial state
    setIsOnline(typeof navigator !== "undefined" ? navigator.onLine : true);
    setWasOnline(typeof navigator !== "undefined" ? navigator.onLine : true);

    const handleOnline = () => {
      setWasOnline(isOnline);
      setIsOnline(true);
      toast.success("Network status: Online");
    };

    const handleOffline = () => {
      setWasOnline(isOnline);
      setIsOnline(false);
      toast.warning("Network status: Offline");
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [isOnline, wasOnline]);

  return (
    <div className="fixed bottom-4 left-4 z-40 flex items-center gap-2 px-3 py-1.5 bg-background/80 backdrop-blur-sm rounded-full border text-sm">
      <span
        className={`w-2 h-2 rounded-full ${
          isOnline ? "bg-green-500" : "bg-red-500"
        }`}
      />
      <span className="text-muted-foreground text-xs">
        {isOnline ? "Online" : "Offline"}
      </span>
    </div>
  );
}