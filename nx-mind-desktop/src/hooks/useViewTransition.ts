"use client";

import { useCallback, useTransition } from "react";
import { usePathname } from "next/navigation";

type ViewTransitionOptions = {
  skipTransition?: boolean;
};

export function useViewTransition() {
  const [isPending, startTransition] = useTransition();
  const pathname = usePathname();

  const viewTransition = useCallback(
    (callback: () => void, options?: ViewTransitionOptions) => {
      if (options?.skipTransition) {
        callback();
        return;
      }

      if (typeof document !== "undefined" && "startViewTransition" in document) {
        (document as any).startViewTransition(() => {
          return new Promise<void>((resolve) => {
            startTransition(() => {
              callback();
              resolve();
            });
          });
        });
      } else {
        startTransition(callback);
      }
    },
    []
  );

  return {
    isPending,
    viewTransition,
    canUseViewTransitions: typeof document !== "undefined" && "startViewTransition" in document,
  };
}

export function cn(...classes: (string | undefined | null | false)[]) {
  return classes.filter(Boolean).join(" ");
}
