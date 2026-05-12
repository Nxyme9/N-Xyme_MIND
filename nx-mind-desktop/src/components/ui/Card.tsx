import * as React from "react"
import { cn } from "@/lib/utils"

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  selected?: boolean
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, selected, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "rounded-xl bg-bg-secondary border border-border p-4 transition-all",
          selected && "border-accent ring-2 ring-accent/20",
          className
        )}
        {...props}
      >
        {children}
      </div>
    )
  }
)
Card.displayName = "Card"

export { Card }