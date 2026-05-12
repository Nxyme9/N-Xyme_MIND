import { create } from "zustand";

export interface Task {
  id: string;
  description: string;
  status: "pending" | "running" | "completed" | "failed";
  priority: "low" | "medium" | "high" | "urgent";
  createdAt: Date;
  assignedTo?: string;
  dependsOn?: string[]; // IDs of tasks this task depends on
}

interface TaskState {
  tasks: Task[];
  addTask: (task: Task) => void;
  updateTask: (id: string, updates: Partial<Task>) => void;
  removeTask: (id: string) => void;
  reorderTasks: (fromIndex: number, toIndex: number) => void;
  setTasks: (tasks: Task[]) => void;
  addDependency: (taskId: string, dependsOnId: string) => void;
  removeDependency: (taskId: string, dependsOnId: string) => void;
  clearCompleted: () => void;
  getDependents: (taskId: string) => Task[];
}

export const useTaskStore = create<TaskState>((set, get) => ({
  tasks: [],
  addTask: (task) => set((state) => ({ tasks: [...state.tasks, task] })),
  updateTask: (id, updates) =>
    set((state) => ({
      tasks: state.tasks.map((task) =>
        task.id === id ? { ...task, ...updates } : task
      ),
    })),
  removeTask: (id) =>
    set((state) => ({
      tasks: state.tasks.filter((task) => task.id !== id),
    })),
  reorderTasks: (fromIndex, toIndex) =>
    set((state) => {
      const newTasks = [...state.tasks];
      const [moved] = newTasks.splice(fromIndex, 1);
      newTasks.splice(toIndex, 0, moved);
      return { tasks: newTasks };
    }),
  setTasks: (tasks) => set({ tasks }),
  addDependency: (taskId, dependsOnId) =>
    set((state) => ({
      tasks: state.tasks.map((task) =>
        task.id === taskId
          ? {
              ...task,
              dependsOn: task.dependsOn
                ? task.dependsOn.includes(dependsOnId)
                  ? task.dependsOn
                  : [...task.dependsOn, dependsOnId]
                : [dependsOnId],
            }
          : task
      ),
    })),
  removeDependency: (taskId, dependsOnId) =>
    set((state) => ({
      tasks: state.tasks.map((task) =>
        task.id === taskId
          ? {
              ...task,
              dependsOn: task.dependsOn?.filter((id) => id !== dependsOnId),
            }
          : task
      ),
    })),
  clearCompleted: () =>
    set((state) => ({
      tasks: state.tasks.filter((task) => task.status !== "completed"),
    })),
  getDependents: (taskId) => {
    const state = get();
    return state.tasks.filter(
      (task) => task.dependsOn?.includes(taskId)
    );
  },
}));