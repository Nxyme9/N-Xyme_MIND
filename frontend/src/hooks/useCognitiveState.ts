"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type CognitiveState = "surge" | "drift" | "dawn";

interface CognitiveStateStore {
  cognitiveState: CognitiveState;
  autoDetected: boolean;
  setCognitiveState: (state: CognitiveState, auto?: boolean) => void;
  setFromOrchestration: (orchestrationState: string) => void;
}

const mapOrchestrationToCognitive = (orchestrationState: string): CognitiveState => {
  switch (orchestrationState.toLowerCase()) {
    case "flow":
      return "surge";
    case "friction":
      return "drift";
    case "adapt":
    case "dawn":
    default:
      return "dawn";
  }
};

export const useCognitiveStateStore = create<CognitiveStateStore>()(
  persist(
    (set) => ({
      cognitiveState: "drift",
      autoDetected: false,

      setCognitiveState: (state, auto = false) =>
        set({ cognitiveState: state, autoDetected: auto }),

      setFromOrchestration: (orchestrationState: string) => {
        const cognitiveState = mapOrchestrationToCognitive(orchestrationState);
        set({ cognitiveState, autoDetected: true });
      },
    }),
    {
      name: "nxyme-cognitive-state",
    }
  )
);

export function useCognitiveState() {
  const cognitiveState = useCognitiveStateStore((state) => state.cognitiveState);
  const autoDetected = useCognitiveStateStore((state) => state.autoDetected);
  const setCognitiveState = useCognitiveStateStore((state) => state.setCognitiveState);
  const setFromOrchestration = useCognitiveStateStore((state) => state.setFromOrchestration);

  return {
    cognitiveState,
    autoDetected,
    isSurge: cognitiveState === "surge",
    isDrift: cognitiveState === "drift",
    isDawn: cognitiveState === "dawn",
    setCognitiveState,
    setFromOrchestration,
  };
}

export function useSyncWithOrchestration() {
  const setFromOrchestration = useCognitiveStateStore((state) => state.setFromOrchestration);

  return { setFromOrchestration };
}