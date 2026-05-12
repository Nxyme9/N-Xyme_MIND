import { create } from "zustand";

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
  setAgents: (agents: Agent[]) => void;
  updateAgent: (id: string, updates: Partial<Agent>) => void;
  setActiveAgent: (id: string | null) => void;
}

export const useAgentStore = create<AgentState>((set) => ({
  agents: [],
  activeAgent: null,
  setAgents: (agents) => set({ agents }),
  updateAgent: (id, updates) =>
    set((state) => ({
      agents: state.agents.map((agent) =>
        agent.id === id ? { ...agent, ...updates } : agent
      ),
    })),
  setActiveAgent: (id) => set({ activeAgent: id }),
}));