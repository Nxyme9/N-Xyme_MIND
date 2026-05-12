"use client";

import { useGlobalLoadingStore } from "@/stores/useGlobalLoadingStore";

export function GlobalLoadingOverlay() {
  const isLoading = useGlobalLoadingStore((state) => state.isLoading);

  if (!isLoading) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="flex flex-col items-center gap-4">
        <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin" />
        <p className="text-sm text-white/80 animate-pulse">Loading...</p>
      </div>
    </div>
  );
}