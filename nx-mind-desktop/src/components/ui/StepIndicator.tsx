import * as React from "react"
import { Check } from "lucide-react"
import { cn } from "@/lib/utils"

interface Step {
  id: number
  label: string
}

interface StepIndicatorProps {
  steps: Step[]
  currentStep: number
  onStepClick?: (step: number) => void
}

export function StepIndicator({ steps, currentStep, onStepClick }: StepIndicatorProps) {
  return (
    <div className="flex items-center justify-center gap-2">
      {steps.map((step, index) => (
        <div key={step.id} className="flex items-center">
          <button
            onClick={() => onStepClick?.(step.id)}
            className={cn(
              "w-10 h-10 rounded-full flex items-center justify-center font-medium transition-all",
              currentStep > step.id && "bg-success text-white",
              currentStep === step.id && "bg-accent text-white",
              currentStep < step.id && "bg-bg-tertiary text-text-secondary"
            )}
          >
            {currentStep > step.id ? <Check className="h-5 w-5" /> : step.id}
          </button>
          {index < steps.length - 1 && (
            <div className={cn(
              "w-8 h-0.5 mx-2",
              currentStep > step.id ? "bg-success" : "bg-bg-tertiary"
            )} />
          )}
        </div>
      ))}
    </div>
  )
}