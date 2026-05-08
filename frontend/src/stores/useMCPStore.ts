import { create } from "zustand";

export interface MCPConnection {
  name: string;
  status: "connected" | "disconnected" | "error";
  lastPing?: Date;
}

interface MCPState {
  connections: MCPConnection[];
  setConnections: (connections: MCPConnection[]) => void;
}

export const useMCPStore = create<MCPState>((set) => ({
  connections: [],
  setConnections: (connections) => set({ connections }),
}));