"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface WorkflowNodeData {
  id: string;
  type: "agent" | "router" | "splitter" | "aggregator" | "llm" | "tool" | "subflow";
  agent?: string;
  task?: string;
  label: string;
  config?: {
    timeout_ms?: number;
    max_retries?: number;
    model?: string;
    temperature?: number;
    condition?: {
      output_key?: string;
      operator?: "equals" | "contains" | "greater_than" | "less_than";
      value?: string;
      branches?: Record<string, string>;
    };
  };
  position?: { x: number; y: number };
}

export interface WorkflowEdgeData {
  id: string;
  source: string;
  target: string;
  type?: "sequential" | "conditional";
  label?: string;
}

export interface WorkflowMetadata {
  id: string;
  name: string;
  description?: string;
  category?: string;
  created_at: string;
  updated_at: string;
}

export interface WorkflowState {
  id: string;
  name: string;
  description?: string;
  nodes: WorkflowNodeData[];
  edges: WorkflowEdgeData[];
  execution_mode: "linear" | "parallel" | "dag";
  config: {
    fail_fast: boolean;
    max_parallel_tasks: number;
  };
  created_at: string;
  updated_at: string;
}

interface WorkflowStore {
  workflows: WorkflowState[];
  currentWorkflow: WorkflowState | null;
  setCurrentWorkflow: (workflow: WorkflowState | null) => void;
  addWorkflow: (workflow: WorkflowState) => void;
  updateWorkflow: (id: string, updates: Partial<WorkflowState>) => void;
  deleteWorkflow: (id: string) => void;
  duplicateWorkflow: (id: string) => void;
}

const createDefaultWorkflow = (): WorkflowState => ({
  id: `wf_${Date.now()}`,
  name: "New Workflow",
  description: "",
  nodes: [],
  edges: [],
  execution_mode: "dag",
  config: {
    fail_fast: true,
    max_parallel_tasks: 5,
  },
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
});

export const useWorkflowStore = create<WorkflowStore>()(
  persist(
    (set, get) => ({
      workflows: [],
      currentWorkflow: null,

      setCurrentWorkflow: (workflow) => set({ currentWorkflow: workflow }),

      addWorkflow: (workflow) =>
        set((state) => ({
          workflows: [...state.workflows, workflow],
        })),

      updateWorkflow: (id, updates) =>
        set((state) => ({
          workflows: state.workflows.map((wf) =>
            wf.id === id ? { ...wf, ...updates, updated_at: new Date().toISOString() } : wf
          ),
          currentWorkflow:
            state.currentWorkflow?.id === id
              ? { ...state.currentWorkflow, ...updates, updated_at: new Date().toISOString() }
              : state.currentWorkflow,
        })),

      deleteWorkflow: (id) =>
        set((state) => ({
          workflows: state.workflows.filter((wf) => wf.id !== id),
          currentWorkflow: state.currentWorkflow?.id === id ? null : state.currentWorkflow,
        })),

      duplicateWorkflow: (id) => {
        const workflow = get().workflows.find((wf) => wf.id === id);
        if (workflow) {
          const newWorkflow: WorkflowState = {
            ...workflow,
            id: `wf_${Date.now()}`,
            name: `${workflow.name} (Copy)`,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          };
          set((state) => ({
            workflows: [...state.workflows, newWorkflow],
          }));
        }
      },
    }),
    {
      name: "nxyme-workflows",
    }
  )
);

export function createNewWorkflow(): WorkflowState {
  return createDefaultWorkflow();
}