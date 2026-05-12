import { useEffect, useCallback } from "react";

interface ShortcutHandler {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
  meta?: boolean;
  handler: () => void;
  description: string;
}

const handlers: ShortcutHandler[] = [];

export function useKeyboardShortcut(
  key: string,
  handler: () => void,
  options: { ctrl?: boolean; shift?: boolean; alt?: boolean; meta?: boolean } = {},
  description: string = ""
) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      const matchesCtrl = options.ctrl ? e.ctrlKey || e.metaKey : true;
      const matchesShift = options.shift ? e.shiftKey : !e.shiftKey;
      const matchesAlt = options.alt ? e.altKey : !e.altKey;
      const matchesMeta = options.meta ? e.metaKey : true;

      if (
        e.key.toLowerCase() === key.toLowerCase() &&
        matchesCtrl &&
        matchesShift &&
        matchesAlt &&
        matchesMeta
      ) {
        e.preventDefault();
        handler();
      }
    },
    [key, handler, options.ctrl, options.shift, options.alt, options.meta]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);
}

export function registerGlobalShortcut(handler: ShortcutHandler) {
  handlers.push(handler);
}

export function unregisterGlobalShortcut(key: string) {
  const index = handlers.findIndex((h) => h.key === key);
  if (index > -1) handlers.splice(index, 1);
}

export const GLOBAL_SHORTCUTS = [
  { key: "k", ctrl: true, description: "Open command palette" },
  { key: "p", ctrl: true, description: "Quick search" },
  { key: "n", ctrl: true, description: "New item" },
  { key: "s", ctrl: true, description: "Save current" },
  { key: "/", ctrl: true, description: "Show shortcuts" },
  { key: "Escape", description: "Close modal/palette" },
  { key: "Enter", description: "Confirm action" },
  { key: "ArrowUp", description: "Navigate up" },
  { key: "ArrowDown", description: "Navigate down" },
  { key: "Tab", description: "Next element" },
];