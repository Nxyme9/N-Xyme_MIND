"use client"

import * as React from "react"

type ToastVariant = "default" | "success" | "error" | "warning"

export interface ToastData {
  id: string
  title?: string
  description?: string
  variant: ToastVariant
  duration: number
}

interface ToastContextType {
  toasts: ToastData[]
  toast: (props: Omit<ToastData, "id">) => void
  dismiss: (id: string) => void
  dismissAll: () => void
}

const ToastContext = React.createContext<ToastContextType | undefined>(undefined)

const MAX_TOASTS = 3

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<ToastData[]>([])

  const toast = React.useCallback((props: Omit<ToastData, "id">) => {
    const id = Math.random().toString(36).substring(2, 11)
    const newToast: ToastData = { ...props, id }

    setToasts(prev => {
      const updated = [...prev, newToast]
      return updated.slice(-MAX_TOASTS)
    })

    if (props.duration > 0) {
      setTimeout(() => {
        dismiss(id)
      }, props.duration + 300)
    }
  }, [])

  const dismiss = React.useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  const dismissAll = React.useCallback(() => {
    setToasts([])
  }, [])

  return (
    <ToastContext.Provider value={{ toasts, toast, dismiss, dismissAll }}>
      {children}
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = React.useContext(ToastContext)
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider")
  }
  return context
}

export function Toaster() {
  const { toasts } = useToast()
  
  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`px-4 py-3 rounded-lg shadow-lg border ${
            t.variant === 'success' ? 'bg-green-500/90 border-green-400 text-white' :
            t.variant === 'error' ? 'bg-red-500/90 border-red-400 text-white' :
            t.variant === 'warning' ? 'bg-yellow-500/90 border-yellow-400 text-white' :
            'bg-slate-800/90 border-slate-700 text-white'
          }`}
        >
          {t.title && <div className="font-semibold text-sm">{t.title}</div>}
          {t.description && <div className="text-xs opacity-90">{t.description}</div>}
        </div>
      ))}
    </div>
  )
}

export type { ToastVariant }
