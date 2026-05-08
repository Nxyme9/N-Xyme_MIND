import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface Agent {
  id: string;
  name: string;
  role?: string;
  status: "idle" | "working" | "error";
  currentTask?: string;
  lastActive?: Date;
}

interface AgentState {
  agents: Agent[];
  activeAgent: string | null;
  executionMode: "flow" | "friction";
  setAgents: (agents: Agent[]) => void;
  updateAgent: (id: string, updates: Partial<Agent>) => void;
  setActiveAgent: (id: string | null) => void;
  setExecutionMode: (mode: "flow" | "friction") => void;
}

export const useAgentStore = create<AgentState>()(
  persist(
    (set) => ({
      agents: [],
      activeAgent: null,
      executionMode: "flow",
      setAgents: (agents) => set({ agents }),
      updateAgent: (id, updates) =>
        set((state) => ({
          agents: state.agents.map((agent) =>
            agent.id === id ? { ...agent, ...updates } : agent
          ),
        })),
      setActiveAgent: (id) => set({ activeAgent: id }),
      setExecutionMode: (mode) => set({ executionMode: mode }),
    }),
    { name: "agent-store" }
  )
);