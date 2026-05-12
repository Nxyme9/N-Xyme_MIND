"use client"

import * as React from "react"
import { Dialog, DialogContent } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Search, Keyboard, X, Command } from "lucide-react"
import { cn } from "@/lib/utils"

interface Shortcut {
  keys: string[]
  description: string
  category: "Navigation" | "Actions" | "Global"
}

const shortcuts: Shortcut[] = [
  {
    keys: ["⌘", "K"],
    description: "Open command palette",
    category: "Actions",
  },
  {
    keys: ["⌘", "/"],
    description: "Show keyboard shortcuts",
    category: "Global",
  },
  {
    keys: ["⌘", "D"],
    description: "Go to Dashboard",
    category: "Navigation",
  },
  {
    keys: ["⌘", "O"],
    description: "Go to Orchestration",
    category: "Navigation",
  },
  {
    keys: ["⌘", "M"],
    description: "Go to Memory",
    category: "Navigation",
  },
  {
    keys: ["⌘", ","],
    description: "Open Settings",
    category: "Navigation",
  },
  {
    keys: ["⌘", "C"],
    description: "Go to Chat",
    category: "Navigation",
  },
  {
    keys: ["Esc"],
    description: "Close modal or palette",
    category: "Global",
  },
  {
    keys: ["↑", "↓"],
    description: "Navigate between items",
    category: "Navigation",
  },
  {
    keys: ["Enter"],
    description: "Select highlighted item",
    category: "Actions",
  },
]

interface KeyboardShortcutsModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function KeyboardShortcutsModal({ open, onOpenChange }: KeyboardShortcutsModalProps) {
  const [query, setQuery] = React.useState("")

  const filteredShortcuts = query
    ? shortcuts.filter(
        (s) =>
          s.description.toLowerCase().includes(query.toLowerCase()) ||
          s.category.toLowerCase().includes(query.toLowerCase()) ||
          s.keys.some((k) => k.toLowerCase().includes(query.toLowerCase()))
      )
    : shortcuts

  const groupedShortcuts = filteredShortcuts.reduce((acc, shortcut) => {
    if (!acc[shortcut.category]) {
      acc[shortcut.category] = []
    }
    acc[shortcut.category].push(shortcut)
    return acc
  }, {} as Record<string, Shortcut[]>)

  const categoryOrder: Shortcut["category"][] = ["Global", "Navigation", "Actions"]

  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "/") {
        e.preventDefault()
        onOpenChange(true)
      }
      if (e.key === "Escape") {
        onOpenChange(false)
        setQuery("")
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [onOpenChange])

  React.useEffect(() => {
    if (!open) {
      setQuery("")
    }
  }, [open])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="p-0 gap-0 max-w-2xl w-[90vw] overflow-hidden border-primary/30">
        <div className="relative">
          <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-cyan-500/5 pointer-events-none" />
          <div className="relative">
            <div className="flex items-center border-b border-primary/20 px-4 py-3">
              <div className="flex items-center gap-2 mr-3">
                <div className="p-2 rounded-lg bg-primary/10 border border-primary/30">
                  <Keyboard className="w-5 h-5 text-primary" />
                </div>
              </div>
              <Input
                className="flex-1 border-0 bg-transparent text-sm outline-none placeholder:text-muted-foreground focus-visible:ring-0 py-2"
                placeholder="Filter shortcuts..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                autoFocus
                aria-label="Filter keyboard shortcuts"
              />
              <div className="flex items-center gap-1 ml-3 text-xs text-muted-foreground">
                <kbd className="px-1.5 py-0.5 bg-secondary rounded border border-border/50 text-[10px] font-mono">
                  ⌘
                </kbd>
                <span>+</span>
                <kbd className="px-1.5 py-0.5 bg-secondary rounded border border-border/50 text-[10px] font-mono">
                  /
                </kbd>
              </div>
            </div>
          </div>
        </div>

        <div className="max-h-[400px] overflow-y-auto p-4">
          {filteredShortcuts.length === 0 ? (
            <div className="py-12 text-center">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-muted/50 mb-3">
                <Search className="w-5 h-5 text-muted-foreground" />
              </div>
              <p className="text-sm text-muted-foreground">No shortcuts found</p>
              <p className="text-xs text-muted-foreground/60 mt-1">
                Try a different search term
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {categoryOrder.map((category) => {
                const items = groupedShortcuts[category]
                if (!items?.length) return null
                return (
                  <div key={category} className="animate-fade-in">
                    <div className="flex items-center gap-2 mb-3">
                      <div
                        className={cn(
                          "w-1 h-4 rounded-full",
                          category === "Global" && "bg-cyan-400",
                          category === "Navigation" && "bg-primary",
                          category === "Actions" && "bg-pink-400"
                        )}
                      />
                      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                        {category}
                      </h3>
                    </div>
                    <div className="grid gap-2">
                      {items.map((shortcut, idx) => (
                        <div
                          key={`${category}-${idx}`}
                          className={cn(
                            "group flex items-center justify-between p-3 rounded-lg",
                            "bg-secondary/30 border border-transparent",
                            "hover:bg-secondary/50 hover:border-primary/20",
                            "transition-all duration-200",
                            "animate-slide-up"
                          )}
                          style={{ animationDelay: `${idx * 50}ms` }}
                        >
                          <span className="text-sm text-secondary-foreground">
                            {shortcut.description}
                          </span>
                          <div className="flex items-center gap-1">
                            {shortcut.keys.map((key, keyIdx) => (
                              <React.Fragment key={keyIdx}>
                                <kbd
                                  className={cn(
                                    "px-2 py-1 text-xs font-mono font-medium rounded",
                                    "bg-background/80 border border-border/50",
                                    "shadow-[0_0_10px_hsl(180,100%,50%,0.1)]",
                                    "group-hover:border-primary/40 group-hover:shadow-[0_0_15px_hsl(280,100%,60%,0.2)]",
                                    "transition-all duration-200"
                                  )}
                                >
                                  {key}
                                </kbd>
                                {keyIdx < shortcut.keys.length - 1 && (
                                  <span className="text-muted-foreground/50 text-xs">+</span>
                                )}
                              </React.Fragment>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        <div className="border-t border-primary/20 px-4 py-3 bg-secondary/20">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5">
                <Command className="w-3 h-3" />
                <span>= Cmd on Mac</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="px-1 py-0.5 bg-muted rounded border border-border/50 text-[10px] font-mono">
                  Ctrl
                </span>
                <span>= Ctrl on Windows/Linux</span>
              </span>
            </div>
            <span className="text-muted-foreground/60">Press Esc to close</span>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export function KeyboardShortcutsHint() {
  const [open, setOpen] = React.useState(false)

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className={cn(
          "fixed bottom-4 left-4 flex items-center gap-2",
          "px-3 py-2 rounded-lg text-xs",
          "bg-secondary/80 backdrop-blur-sm border border-border/50",
          "hover:bg-secondary hover:border-primary/30",
          "transition-all duration-200"
        )}
        aria-label="Show keyboard shortcuts"
      >
        <Keyboard className="w-3.5 h-3.5 text-primary" />
        <span className="text-muted-foreground hidden sm:inline">Shortcuts</span>
        <kbd className="hidden md:flex items-center gap-0.5 ml-1 px-1.5 py-0.5 bg-muted rounded border border-border/50 text-[10px] font-mono">
          ⌘/
        </kbd>
      </button>
      <KeyboardShortcutsModal open={open} onOpenChange={setOpen} />
    </>
  )
}
