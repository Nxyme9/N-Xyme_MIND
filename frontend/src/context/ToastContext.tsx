"use client"

import * as React from "react"

export type ToastType = "success" | "error" | "warning" | "info"

export interface Toast {
  id: string
  type: ToastType
  message: string
  duration?: number
}

interface ToastContextType {
  toasts: Toast[]
  addToast: (type: ToastType, message: string, duration?: number) => void
  removeToast: (id: string) => void
}

const ToastContext = React.createContext<ToastContextType | undefined>(undefined)

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<Toast[]>([])

  const addToast = React.useCallback((type: ToastType, message: string, duration = 5000) => {
    const id = Math.random().toString(36).substring(2, 9)
    const newToast: Toast = { id, type, message, duration }
    
    setToasts(prev => [...prev, newToast])

    if (duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, duration)
    }
  }, [])

  const removeToast = React.useCallback((id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
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
          className={`px-4 py-3 rounded-lg shadow-lg border animate-in fade-in slide-in-from-right-4 ${
            t.type === 'success' ? 'bg-green-500/90 border-green-400 text-white' :
            t.type === 'error' ? 'bg-red-500/90 border-red-400 text-white' :
            t.type === 'warning' ? 'bg-yellow-500/90 border-yellow-400 text-white' :
            'bg-slate-800/90 border-slate-700 text-white'
          }`}
        >
          <div className="text-sm font-medium">{t.message}</div>
        </div>
      ))}
    </div>
  )
}