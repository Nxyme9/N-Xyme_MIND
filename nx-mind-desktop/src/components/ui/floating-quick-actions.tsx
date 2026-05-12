"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { 
  Plus, 
  MessageSquare, 
  RotateCcw, 
  Settings,
  Zap
} from "lucide-react";
import { cn } from "@/lib/utils";

interface QuickAction {
  id: string;
  label: string;
  icon: React.ReactNode;
  shortcut: string;
  action: () => void;
}

export function FloatingQuickActions() {
  const [isExpanded, setIsExpanded] = useState(false);
  const router = useRouter();

  const actions: QuickAction[] = [
    {
      id: "new-task",
      label: "New Task",
      icon: <Plus className="w-5 h-5" />,
      shortcut: "T",
      action: () => router.push("/orchestration?new=true"),
    },
    {
      id: "new-chat",
      label: "New Chat",
      icon: <MessageSquare className="w-5 h-5" />,
      shortcut: "C",
      action: () => router.push("/chat?new=true"),
    },
    {
      id: "refresh",
      label: "Refresh",
      icon: <RotateCcw className="w-5 h-5" />,
      shortcut: "R",
      action: () => window.location.reload(),
    },
    {
      id: "settings",
      label: "Settings",
      icon: <Settings className="w-5 h-5" />,
      shortcut: "S",
      action: () => router.push("/settings"),
    },
  ];

  const handleKeyDown = (e: KeyboardEvent) => {
    if (!isExpanded) return;
    
    const key = e.key.toUpperCase();
    const action = actions.find((a) => a.shortcut === key);
    if (action) {
      action.action();
      setIsExpanded(false);
    }
    if (e.key === "Escape") {
      setIsExpanded(false);
    }
  };

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isExpanded]);

  return (
    <div className="fixed bottom-20 right-6 z-40 flex flex-col items-end gap-2">
      <div
        className={cn(
          "flex flex-col gap-2 transition-all duration-150 ease-out",
          isExpanded ? "opacity-100 scale-100" : "opacity-0 scale-95 pointer-events-none"
        )}
      >
        {actions.map((action, index) => (
          <button
            key={action.id}
            onClick={action.action}
            className="group flex items-center gap-3 px-4 py-3 rounded-xl bg-card/80 backdrop-blur-xl border border-border/50 hover:border-primary/50 hover:bg-card transition-all duration-150"
            style={{ animationDelay: `${index * 30}ms` }}
          >
            <span className="text-muted-foreground group-hover:text-primary transition-colors">
              {action.icon}
            </span>
            <span className="text-sm font-medium text-foreground whitespace-nowrap">
              {action.label}
            </span>
            <span className="ml-2 px-2 py-0.5 rounded-md bg-muted/50 text-xs text-muted-foreground font-mono">
              {action.shortcut}
            </span>
          </button>
        ))}
      </div>

      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          "relative flex items-center justify-center w-12 h-12 rounded-full",
          "bg-card/90 backdrop-blur-xl border border-border/60",
          "hover:border-primary/60 hover:shadow-[0_0_20px_hsl(var(--primary)_0.3)]",
          "transition-all duration-150 ease-out",
          "focus:outline-none focus:ring-2 focus:ring-primary/50 focus:ring-offset-2 focus:ring-offset-background",
          isExpanded && "bg-primary/20 border-primary/80"
        )}
        aria-label={isExpanded ? "Close quick actions" : "Open quick actions"}
        aria-expanded={isExpanded}
      >
        <span className="absolute inset-0 rounded-full animate-pulse">
          <span className="absolute inset-0 rounded-full bg-primary/30 animate-ping" />
        </span>
        
        <div className="absolute inset-0 rounded-full bg-gradient-to-br from-primary/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
        
        <Zap 
          className={cn(
            "w-6 h-6 text-primary transition-transform duration-150",
            isExpanded && "rotate-90"
          )} 
        />
      </button>

      {!isExpanded && (
        <span className="absolute -left-20 top-1/2 -translate-y-1/2 text-xs text-muted-foreground/60 font-mono">
          ?
        </span>
      )}
    </div>
  );
}

export default FloatingQuickActions;