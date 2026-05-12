"use client"

import * as React from "react"
import { Toast } from "./toast"
import { useToast, ToastProvider } from "./use-toast"

function ToasterContainer() {
  const { toasts, dismiss } = useToast()

  return (
    <div
      className="fixed top-4 right-4 z-[100] flex flex-col gap-3 w-full max-w-sm pointer-events-none"
      aria-label="Notifications"
    >
      {toasts.map((t) => (
        <div key={t.id} className="pointer-events-auto">
          <Toast
            id={t.id}
            variant={t.variant}
            title={t.title}
            description={t.description}
            duration={t.duration}
            onClose={() => dismiss(t.id)}
          />
        </div>
      ))}
    </div>
  )
}

export function Toaster() {
  return (
    <ToastProvider>
      <ToasterContainer />
    </ToastProvider>
  )
}

export { ToasterContainer }
