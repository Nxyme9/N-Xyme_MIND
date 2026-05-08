"use client";

import { useState, createContext, useContext, type ReactNode } from "react";
import { useCognitiveState } from "@/hooks/useCognitiveState";
import { cn } from "@/lib/utils";

interface TaskScaffoldContextValue {
  currentLayer: number;
  maxLayers: number;
  expandedLayers: number[];
  expandLayer: (layer: number) => void;
  collapseLayer: (layer: number) => void;
  toggleLayer: (layer: number) => void;
}

const TaskScaffoldContext = createContext<TaskScaffoldContextValue | null>(null);

function useTaskScaffoldContext() {
  const context = useContext(TaskScaffoldContext);
  if (!context) {
    throw new Error("TaskScaffold components must be used within TaskScaffold");
  }
  return context;
}

interface Layer {
  id: string;
  name: string;
  content: ReactNode;
  maxFeatures?: number;
}

interface TaskScaffoldProps {
  layers: Layer[];
  className?: string;
  defaultExpanded?: number;
}

const LAYER_CONFIG = {
  surge: 3,
  drift: 2,
  dawn: 1,
};

export function TaskScaffold({ layers, className, defaultExpanded = 0 }: TaskScaffoldProps) {
  const { cognitiveState } = useCognitiveState();
  const [currentLayer, setCurrentLayer] = useState(defaultExpanded);
  const [expandedLayers, setExpandedLayers] = useState<number[]>([defaultExpanded]);

  const maxLayers = LAYER_CONFIG[cognitiveState];

  const expandLayer = (layer: number) => {
    if (layer <= maxLayers) {
      setCurrentLayer(layer);
      if (!expandedLayers.includes(layer)) {
        setExpandedLayers([...expandedLayers, layer]);
      }
    }
  };

  const collapseLayer = (layer: number) => {
    if (layer > 0) {
      setCurrentLayer(layer - 1);
    }
  };

  const toggleLayer = (layer: number) => {
    if (expandedLayers.includes(layer)) {
      if (layer === currentLayer && layer > 0) {
        collapseLayer(layer);
      } else {
        setExpandedLayers(expandedLayers.filter((l) => l !== layer));
      }
    } else {
      expandLayer(layer);
    }
  };

  const visibleLayers = layers.slice(0, maxLayers);

  return (
    <TaskScaffoldContext.Provider
      value={{ currentLayer, maxLayers, expandedLayers, expandLayer, collapseLayer, toggleLayer }}
    >
      <div className={cn("space-y-2", className)}>
        <TaskScaffoldHorizon layers={visibleLayers} />
        <div className="space-y-2">{visibleLayers.map((layer) => layer.content)}</div>
      </div>
    </TaskScaffoldContext.Provider>
  );
}

function TaskScaffoldHorizon({ layers }: { layers: Layer[] }) {
  const { currentLayer, expandedLayers, toggleLayer } = useTaskScaffoldContext();

  return (
    <div className="flex items-center gap-2 p-2 rounded-lg bg-card border border-border">
      {layers.map((layer, index) => {
        const isCompleted = index < currentLayer;
        const isCurrent = index === currentLayer;
        const isExpanded = expandedLayers.includes(index);

        return (
          <button
            key={layer.id}
            onClick={() => toggleLayer(index)}
            className={cn(
              "flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-all",
              isCompleted && "text-muted-foreground",
              isCurrent && !isExpanded && "bg-primary/20 text-primary",
              isExpanded && "bg-primary text-primary-foreground",
              !isCurrent && !isExpanded && "hover:bg-muted"
            )}
          >
            <span
              className={cn(
                "w-2 h-2 rounded-full",
                isCompleted && "bg-green-500",
                isCurrent && !isExpanded && "bg-primary animate-pulse",
                isExpanded && "bg-primary-foreground",
                !isCurrent && !isExpanded && "bg-muted-foreground"
              )}
            />
            <span className="hidden sm:inline">{layer.name}</span>
          </button>
        );
      })}
    </div>
  );
}

interface TaskScaffoldLayerProps {
  layerId: string;
  name: string;
  children: ReactNode;
  features?: ReactNode[];
}

export function TaskScaffoldLayer({ layerId, name, children, features }: TaskScaffoldLayerProps) {
  const { currentLayer, expandedLayers, maxLayers } = useTaskScaffoldContext();
  const layerIndex = parseInt(layerId.split("-")[1]) || 0;
  const isExpanded = expandedLayers.includes(layerIndex);
  const isActive = layerIndex === currentLayer;
  const isVisible = layerIndex <= maxLayers && (isExpanded || layerIndex === currentLayer);

  if (!isVisible) return null;

  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-card overflow-hidden transition-all duration-250",
        isExpanded ? "ring-1 ring-primary/50" : "opacity-80"
      )}
    >
      <div
        className={cn(
          "flex items-center justify-between px-4 py-2 cursor-pointer",
          isActive && "bg-primary/10 border-b border-border"
        )}
        onClick={() => {
          const { toggleLayer } = useTaskScaffoldContext();
          toggleLayer(layerIndex);
        }}
      >
        <h3 className="font-medium text-sm">{name}</h3>
        {features && features.length > 0 && (
          <span className="text-xs text-muted-foreground">{features.length} features</span>
        )}
      </div>
      <div className={cn("p-4", !isExpanded && "hidden")}>{children}</div>
    </div>
  );
}