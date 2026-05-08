"use client";

import { useState, useEffect, useCallback, createContext, useContext, type ReactNode } from "react";
import { cn } from "@/lib/utils";

interface Notification {
  id: string;
  message: string;
  type: "info" | "success" | "warning" | "error";
  duration?: number;
}

interface FocusShieldContextValue {
  notifications: Notification[];
  currentNotification: Notification | null;
  addNotification: (notification: Omit<Notification, "id">) => string;
  removeNotification: (id: string) => void;
  clearAll: () => void;
  isCalmMode: boolean;
  toggleCalmMode: () => void;
  calmModeTimeRemaining: number | null;
}

const FocusShieldContext = createContext<FocusShieldContextValue | null>(null);

function useFocusShieldContext() {
  const context = useContext(FocusShieldContext);
  if (!context) {
    throw new Error("FocusShield components must be used within FocusShieldProvider");
  }
  return context;
}

interface FocusShieldProviderProps {
  children: ReactNode;
  maxQueueSize?: number;
}

const CALM_MODE_DURATION = 25 * 60 * 1000;

export function FocusShieldProvider({ children, maxQueueSize = 10 }: FocusShieldProviderProps) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [currentNotification, setCurrentNotification] = useState<Notification | null>(null);
  const [isCalmMode, setIsCalmMode] = useState(false);
  const [calmModeTimeRemaining, setCalmModeTimeRemaining] = useState<number | null>(null);

  const addNotification = useCallback((notification: Omit<Notification, "id">) => {
    const id = `notif-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setNotifications((prev) => {
      const updated = [...prev, { ...notification, id }];
      return updated.slice(-maxQueueSize);
    });
    return id;
  }, [maxQueueSize]);

  const removeNotification = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
    if (currentNotification?.id === id) {
      setCurrentNotification(null);
    }
  }, [currentNotification]);

  const clearAll = useCallback(() => {
    setNotifications([]);
    setCurrentNotification(null);
  }, []);

  const toggleCalmMode = useCallback(() => {
    setIsCalmMode((prev) => {
      if (!prev) {
        setCalmModeTimeRemaining(CALM_MODE_DURATION);
      } else {
        setCalmModeTimeRemaining(null);
      }
      return !prev;
    });
  }, []);

  useEffect(() => {
    if (notifications.length > 0 && !currentNotification) {
      const next = notifications[0];
      setCurrentNotification(next);
      setNotifications((prev) => prev.slice(1));

      const duration = next.duration || 3000;
      const timer = setTimeout(() => {
        setCurrentNotification(null);
      }, duration);

      return () => clearTimeout(timer);
    }
  }, [notifications, currentNotification]);

  useEffect(() => {
    if (isCalmMode && calmModeTimeRemaining !== null && calmModeTimeRemaining > 0) {
      const timer = setInterval(() => {
        setCalmModeTimeRemaining((prev) => {
          if (prev === null || prev <= 1000) {
            setIsCalmMode(false);
            return null;
          }
          return prev - 1000;
        });
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [isCalmMode, calmModeTimeRemaining]);

  return (
    <FocusShieldContext.Provider
      value={{
        notifications,
        currentNotification,
        addNotification,
        removeNotification,
        clearAll,
        isCalmMode,
        toggleCalmMode,
        calmModeTimeRemaining,
      }}
    >
      {children}
    </FocusShieldContext.Provider>
  );
}

export function FocusShieldNotification() {
  const { currentNotification, isCalmMode } = useFocusShieldContext();

  if (!currentNotification || isCalmMode) return null;

  const typeStyles = {
    info: "bg-blue-500/20 border-blue-500",
    success: "bg-green-500/20 border-green-500",
    warning: "bg-yellow-500/20 border-yellow-500",
    error: "bg-red-500/20 border-red-500",
  };

  return (
    <div
      className={cn(
        "fixed bottom-4 right-4 z-50 animate-toast-enter rounded-lg border p-4 shadow-lg",
        typeStyles[currentNotification.type]
      )}
      role="alert"
    >
      <p className="text-sm font-medium">{currentNotification.message}</p>
    </div>
  );
}

export function useFocusShield() {
  return useFocusShieldContext();
}