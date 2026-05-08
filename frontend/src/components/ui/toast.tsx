"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from "lucide-react"

import { cn } from "@/lib/utils"

export type ToastVariant = "default" | "success" | "error" | "warning"

export interface ToastProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof toastVariants> {
  id: string
  title?: string
  description?: string
  duration?: number
  onClose?: () => void
}

const toastVariants = cva(
  "relative flex items-start gap-3 p-4 rounded-lg border shadow-lg overflow-hidden transition-all duration-300 ease-out",
  {
    variants: {
      variant: {
        default: "glass border-white/10",
        success: "glass border-green-500/50 shadow-[0_0_15px_rgba(34,197,94,0.3)]",
        error: "glass border-red-500/50 shadow-[0_0_15px_rgba(239,68,68,0.3)]",
        warning: "glass border-yellow-500/50 shadow-[0_0_15px_rgba(234,179,8,0.3)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

const iconMap: Record<ToastVariant, React.ReactNode> = {
  default: <Info className="w-5 h-5 text-primary" />,
  success: <CheckCircle className="w-5 h-5 text-green-500" />,
  error: <AlertCircle className="w-5 h-5 text-red-500" />,
  warning: <AlertTriangle className="w-5 h-5 text-yellow-500" />,
}

const progressBarMap: Record<ToastVariant, string> = {
  default: "bg-primary",
  success: "bg-green-500",
  error: "bg-red-500",
  warning: "bg-yellow-500",
}

function Toast({ 
  className, 
  variant, 
  id, 
  title, 
  description, 
  duration = 5000, 
  onClose,
  children,
  ...props 
}: ToastProps) {
  const [isExiting, setIsExiting] = React.useState(false)
  const [progress, setProgress] = React.useState(100)
  const timerRef = React.useRef<NodeJS.Timeout | null>(null)
  const startTimeRef = React.useRef<number>(Date.now())
  const remainingRef = React.useRef<number>(duration)

  React.useEffect(() => {
    if (duration <= 0) return

    const updateProgress = () => {
      const elapsed = Date.now() - startTimeRef.current
      const remaining = Math.max(0, remainingRef.current - elapsed)
      setProgress((remaining / duration) * 100)

      if (remaining <= 0) {
        handleClose()
      } else {
        timerRef.current = setTimeout(updateProgress, 50)
      }
    }

    timerRef.current = setTimeout(updateProgress, 50)

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current)
        const elapsed = Date.now() - startTimeRef.current
        remainingRef.current = remainingRef.current - elapsed
      }
    }
  }, [duration])

  const handleClose = React.useCallback(() => {
    if (isExiting) return
    setIsExiting(true)
    if (timerRef.current) clearTimeout(timerRef.current)
    setTimeout(() => {
      onClose?.()
    }, 300)
  }, [isExiting, onClose])

  const handlePause = React.useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      const elapsed = Date.now() - startTimeRef.current
      remainingRef.current = remainingRef.current - elapsed
    }
  }, [])

  const handleResume = React.useCallback(() => {
    startTimeRef.current = Date.now()
    if (duration > 0) {
      timerRef.current = setTimeout(() => {
        setProgress(prev => {
          if (prev <= 0) {
            handleClose()
            return 0
          }
          return prev - (50 / duration) * 100
        })
      }, 50)
    }
  }, [duration, handleClose])

  return (
    <div
      role="alert"
      aria-live="polite"
      className={cn(
        toastVariants({ variant }),
        isExiting ? "animate-toast-exit opacity-0 translate-x-full" : "animate-toast-enter",
        className
      )}
      onMouseEnter={handlePause}
      onMouseLeave={handleResume}
      {...props}
    >
      <span className="shrink-0 mt-0.5">{iconMap[variant || "default"]}</span>
      
      <div className="flex-1 min-w-0">
        {title && (
          <p className="text-sm font-medium text-foreground">{title}</p>
        )}
        {description && (
          <p className={cn("text-sm text-muted-foreground mt-0.5", !title && "mt-0")}>
            {description}
          </p>
        )}
        {children}
      </div>

      <button
        onClick={handleClose}
        className="shrink-0 p-1 rounded-md hover:bg-white/10 transition-colors focus:outline-none focus:ring-2 focus:ring-primary/50"
        aria-label="Dismiss notification"
      >
        <X className="w-4 h-4 text-muted-foreground hover:text-foreground transition-colors" />
      </button>

      {duration > 0 && (
        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-black/20">
          <div
            className={cn("h-full transition-all duration-50 ease-linear", progressBarMap[variant || "default"])}
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </div>
  )
}

Toast.displayName = "Toast"

export { Toast, toastVariants }
