"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { isLocalStorageAvailable } from "@/lib/utils";

interface AutoSaveOptions {
  key: string;
  debounceMs?: number;
  maxEntries?: number;
  storageKey?: string;
}

interface AutoSaveState {
  lastSaved: number | null;
  isSaving: boolean;
  error: string | null;
  entryCount: number;
}

export function useAutoSave<T>(initialValue: T, options: AutoSaveOptions) {
  const { key, debounceMs = 2000, maxEntries = 50, storageKey = "nxyme-autosave" } = options;
  const canUseStorage = isLocalStorageAvailable();
  const [value, setValue] = useState<T>(initialValue);
  const [state, setState] = useState<AutoSaveState>({
    lastSaved: null,
    isSaving: false,
    error: null,
    entryCount: 0,
  });
  const debounceTimer = useRef<NodeJS.Timeout | null>(null);
  const valueRef = useRef<T>(initialValue);

  useEffect(() => {
    if (!canUseStorage) return;
    const stored = localStorage.getItem(`${storageKey}-${key}`);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (parsed.value !== undefined) {
          setValue(parsed.value);
          valueRef.current = parsed.value;
          setState((s) => ({ ...s, lastSaved: parsed.timestamp, entryCount: 1 }));
        }
      } catch {
        console.error("Failed to parse stored auto-save");
      }
    }
  }, [key, storageKey]);

const saveNow = useCallback(() => {
    if (!canUseStorage) {
      setState((s) => ({ ...s, error: "Storage unavailable" }));
      return;
    }

    setState((s) => ({ ...s, isSaving: true, error: null }));

    try {
      const timestamp = Date.now();
      const entry = { value: valueRef.current, timestamp, key };
      localStorage.setItem(`${storageKey}-${key}`, JSON.stringify(entry));

      const keysToKeep: string[] = [];
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        if (k?.startsWith(`${storageKey}-`)) {
          const entryKey = k.replace(`${storageKey}-`, "");
          if (!keysToKeep.includes(entryKey)) {
            keysToKeep.push(entryKey);
          }
        }
      }

      if (keysToKeep.length > maxEntries) {
        const sorted = keysToKeep.sort((a, b) => {
          const aTime = JSON.parse(localStorage.getItem(`${storageKey}-${a}`) || "{}").timestamp || 0;
          const bTime = JSON.parse(localStorage.getItem(`${storageKey}-${b}`) || "{}").timestamp || 0;
          return bTime - aTime;
        });
        sorted.slice(maxEntries).forEach((k) => localStorage.removeItem(`${storageKey}-${k}`));
      }

      setState((s) => ({ ...s, lastSaved: timestamp, isSaving: false, entryCount: keysToKeep.length }));
    } catch (e) {
      setState((s) => ({
        ...s,
        isSaving: false,
        error: e instanceof Error ? e.message : "Save failed",
      }));
    }
  }, [key, storageKey, maxEntries]);

  const updateValue = useCallback(
    (newValue: T | ((prev: T) => T)) => {
      const resolvedValue = typeof newValue === "function" ? (newValue as (prev: T) => T)(valueRef.current) : newValue;
      valueRef.current = resolvedValue;
      setValue(resolvedValue);

      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }

      debounceTimer.current = setTimeout(saveNow, debounceMs);
    },
    [debounceMs, saveNow]
  );

  useEffect(() => {
    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
        saveNow();
      }
    };
  }, [saveNow]);

  const clearSave = useCallback(() => {
    if (!canUseStorage) return;
    localStorage.removeItem(`${storageKey}-${key}`);
    setState({ lastSaved: null, isSaving: false, error: null, entryCount: 0 });
  }, [key, storageKey]);

  return { value: value as T, setValue: updateValue, state, saveNow, clearSave };
}

export function useAutoSaveIndicator() {
  const [lastSaved, setLastSaved] = useState<number | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    const handleStorage = (e: StorageEvent) => {
      if (e.key?.startsWith("nxyme-autosave-")) {
        if (e.newValue) {
          const parsed = JSON.parse(e.newValue);
          setLastSaved(parsed.timestamp);
        }
      }
    };

    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  return { lastSaved, isSaving };
}