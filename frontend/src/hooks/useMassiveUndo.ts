"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  addSnapshot,
  getLatestSnapshot,
  addAction,
  getActionsByEntity,
  addUndo,
  getPendingUndos,
  markUndoAsDone,
  clearOldSnapshots,
  type Snapshot,
  type Action,
  type UndoEntry,
} from "@/lib/db/schema";

interface MassiveUndoOptions {
  maxStates?: number;
  historyDurationMs?: number;
  autoCleanupIntervalMs?: number;
}

interface MassiveUndoState {
  canUndo: boolean;
  canRedo: boolean;
  historyCount: number;
  lastSnapshot: number | null;
  isLoading: boolean;
}

export function useMassiveUndo(options: MassiveUndoOptions = {}) {
  const { maxStates = 50, historyDurationMs = 60 * 60 * 1000, autoCleanupIntervalMs = 60000 } = options;

  const [state, setState] = useState<MassiveUndoState>({
    canUndo: false,
    canRedo: false,
    historyCount: 0,
    lastSnapshot: null,
    isLoading: true,
  });

  const pendingUndosRef = useRef<UndoEntry[]>([]);

  const refreshState = useCallback(async () => {
    try {
      const latest = await getLatestSnapshot();
      const pending = await getPendingUndos();
      pendingUndosRef.current = pending;

      setState((s) => ({
        ...s,
        canUndo: !!latest,
        canRedo: pending.some((p) => !p.undone),
        historyCount: pending.length,
        lastSnapshot: latest?.timestamp || null,
        isLoading: false,
      }));
    } catch (e) {
      console.error("Failed to refresh massive undo state:", e);
      setState((s) => ({ ...s, isLoading: false }));
    }
  }, []);

  useEffect(() => {
    refreshState();
  }, [refreshState]);

  useEffect(() => {
    if (autoCleanupIntervalMs > 0) {
      const interval = setInterval(async () => {
        try {
          await clearOldSnapshots(historyDurationMs);
        } catch (e) {
          console.error("Auto-cleanup failed:", e);
        }
      }, autoCleanupIntervalMs);
      return () => clearInterval(interval);
    }
  }, [historyDurationMs, autoCleanupIntervalMs]);

  const createSnapshot = useCallback(
    async (description: string, stateData?: unknown) => {
      try {
        const id = await addSnapshot({
          timestamp: Date.now(),
          state: JSON.stringify(stateData),
          description,
        });
        await refreshState();
        return id;
      } catch (e) {
        console.error("Failed to create snapshot:", e);
        return null;
      }
    },
    [refreshState]
  );

  const recordAction = useCallback(
    async (action: Omit<Action, "id">) => {
      try {
        const id = await addAction(action);
        await refreshState();
        return id;
      } catch (e) {
        console.error("Failed to record action:", e);
        return null;
      }
    },
    [refreshState]
  );

  const undo = useCallback(
    async (description: string) => {
      try {
        const latest = await getLatestSnapshot();
        if (!latest) return false;

        const actionIds = latest.id ? [latest.id] : [];
        await addUndo({
          timestamp: Date.now(),
          actionIds,
          description,
          undone: false,
        });
        await refreshState();
        return true;
      } catch (e) {
        console.error("Failed to undo:", e);
        return false;
      }
    },
    [refreshState]
  );

  const redo = useCallback(async () => {
    try {
      const pending = await getPendingUndos();
      const toRedo = pending.filter((p) => !p.undone);
      if (toRedo.length === 0) return false;

      for (const entry of toRedo) {
        if (entry.id) {
          await markUndoAsDone(entry.id);
        }
      }
      await refreshState();
      return true;
    } catch (e) {
      console.error("Failed to redo:", e);
      return false;
    }
  }, [refreshState]);

  const getEntityHistory = useCallback(async (entityType: string, entityId: string) => {
    try {
      return await getActionsByEntity(entityType, entityId);
    } catch (e) {
      console.error("Failed to get entity history:", e);
      return [];
    }
  }, []);

  return {
    ...state,
    createSnapshot,
    recordAction,
    undo,
    redo,
    getEntityHistory,
    refreshState,
  };
}

export function useMassiveUndoButton() {
  const { canUndo, canRedo, historyCount, undo, redo } = useMassiveUndo();

  const handleUndo = useCallback(async () => {
    const success = await undo("Manual undo via button");
    return success;
  }, [undo]);

  const handleRedo = useCallback(async () => {
    const success = await redo();
    return success;
  }, [redo]);

  return {
    canUndo,
    canRedo,
    historyCount,
    handleUndo,
    handleRedo,
  };
}