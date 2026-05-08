"use client"

import * as React from "react"
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from "lucide-react"
import { useToast, Toast, ToastType } from "@/context/ToastContext"

const iconMap: Record<ToastType, React.ReactNode> = {
  success: <CheckCircle className="w-5 h-5 text-green-500" />,
  error: <AlertCircle className="w-5 h-5 text-red-500" />,
  warning: <AlertTriangle className="w-5 h-5 text-yellow-500" />,
  info: <Info className="w-5 h-5 text-blue-500" />,
}

const styleMap: Record<ToastType, string> = {
  success: "bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800",
  error: "bg-red-50 dark:bg-red-950 border-red-200 dark:border-red-800",
  warning: "bg-yellow-50 dark:bg-yellow-950 border-yellow-200 dark:border-yellow-800",
  info: "bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800",
}

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: () => void }) {
  return (
    <div
      role="alert"
      aria-live="polite"
      className={`flex items-start gap-3 p-4 rounded-lg border shadow-lg ${styleMap[toast.type]} animate-slide-in-right`}
    >
      <span className="shrink-0 mt-0.5">{iconMap[toast.type]}</span>
      <p className="flex-1 text-sm text-foreground">{toast.message}</p>
      <button
        onClick={onDismiss}
        className="shrink-0 p-1 rounded hover:bg-muted transition-colors focus:outline-none focus:ring-2 focus:ring-ring"
        aria-label="Dismiss notification"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  )
}

export function ToastContainer() {
  const { toasts, removeToast } = useToast()

  if (toasts.length === 0) return null

  return (
    <div
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 w-full max-w-sm"
      aria-label="Notifications"
    >
      {toasts.map((toast) => (
        <ToastItem
          key={toast.id}
          toast={toast}
          onDismiss={() => removeToast(toast.id)}
        />
      ))}
    </div>
  )
}