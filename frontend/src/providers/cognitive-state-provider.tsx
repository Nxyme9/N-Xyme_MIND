"use client";

import { useEffect } from "react";
import { useCognitiveState } from "@/hooks/useCognitiveState";
import { useCognitiveBandwidth } from "@/hooks/useCognitiveBandwidth";

interface CognitiveStateProviderProps {
  children: React.ReactNode;
}

export function CognitiveStateProvider({ children }: CognitiveStateProviderProps) {
  const { cognitiveState, setCognitiveState } = useCognitiveState();
  const bandwidthResult = useCognitiveBandwidth(3000);

  useEffect(() => {
    if (bandwidthResult.confidence > 0.7) {
      const detectedState = bandwidthResult.state;
      if (detectedState !== cognitiveState) {
        setCognitiveState(detectedState, true);
      }
    }
  }, [bandwidthResult, cognitiveState, setCognitiveState]);

  useEffect(() => {
    document.documentElement.setAttribute("data-cognitive-state", cognitiveState);
  }, [cognitiveState]);

  return <>{children}</>;
}