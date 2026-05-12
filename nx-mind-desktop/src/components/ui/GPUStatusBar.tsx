import { cn } from "@/lib/utils"

interface GPUStatusBarProps {
  used: number
  total: number
  className?: string
}

export function GPUStatusBar({ used, total, className }: GPUStatusBarProps) {
  const percentage = (used / total) * 100
  const getColor = () => {
    if (percentage > 90) return "bg-danger"
    if (percentage > 70) return "bg-warning"
    return "bg-success"
  }
  
  return (
    <div className={cn("space-y-1", className)}>
      <div className="flex justify-between text-sm">
        <span className="text-text-secondary">VRAM</span>
        <span className="text-text-primary font-mono">{used.toFixed(0)} / {total.toFixed(0)} GB</span>
      </div>
      <div className="h-2 rounded-full bg-bg-tertiary overflow-hidden">
        <div
          className={cn("h-full transition-all", getColor())}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}