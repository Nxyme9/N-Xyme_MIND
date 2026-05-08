import { create } from "zustand";

interface GlobalLoadingState {
  isLoading: boolean;
  setLoading: (loading: boolean) => void;
  clearLoading: () => void;
}

export const useGlobalLoadingStore = create<GlobalLoadingState>((set) => ({
  isLoading: false,
  setLoading: (loading) => set({ isLoading: loading }),
  clearLoading: () => set({ isLoading: false }),
}));

// Hook for easy access
export const useGlobalLoading = () => {
  const isLoading = useGlobalLoadingStore((state) => state.isLoading);
  const setLoading = useGlobalLoadingStore((state) => state.setLoading);
  const clearLoading = useGlobalLoadingStore((state) => state.clearLoading);
  return { isLoading, setLoading, clearLoading };
};