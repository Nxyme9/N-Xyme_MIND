"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { Dialog, DialogContent } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { 
  LayoutDashboard, 
  GitBranch, 
  Brain, 
  MessageSquare, 
  Search,
  Keyboard,
  Plus,
  Settings,
  Play,
  Square,
  Focus,
  ListTodo,
  CheckCircle2,
  Layers,
  Save,
  FolderOpen,
  Eye
} from "lucide-react"

interface CommandItem {
  id: string
  label: string
  icon: React.ReactNode
  action: () => void
  shortcut?: string
  category: string
}

export function CommandPalette() {
  const router = useRouter()
  const [open, setOpen] = React.useState(false)
  const [query, setQuery] = React.useState("")
  const [selectedIndex, setSelectedIndex] = React.useState(0)

  const commands: CommandItem[] = [
    {
      id: "dashboard",
      label: "Go to Dashboard",
      icon: <LayoutDashboard className="w-4 h-4" />,
      action: () => router.push("/dashboard"),
      shortcut: "G D",
      category: "Navigation"
    },
    {
      id: "orchestration",
      label: "Go to Orchestration",
      icon: <GitBranch className="w-4 h-4" />,
      action: () => router.push("/orchestration"),
      shortcut: "G O",
      category: "Navigation"
    },
    {
      id: "memory",
      label: "Go to Memory",
      icon: <Brain className="w-4 h-4" />,
      action: () => router.push("/memory"),
      shortcut: "G M",
      category: "Navigation"
    },
    {
      id: "chat",
      label: "Go to Chat",
      icon: <MessageSquare className="w-4 h-4" />,
      action: () => router.push("/chat"),
      shortcut: "G C",
      category: "Navigation"
    },
    {
      id: "settings",
      label: "Go to Settings",
      icon: <Settings className="w-4 h-4" />,
      action: () => router.push("/settings"),
      shortcut: "G S",
      category: "Navigation"
    },
    {
      id: "new-task",
      label: "New Task",
      icon: <Plus className="w-4 h-4" />,
      action: () => router.push("/orchestration?new=true"),
      shortcut: "N T",
      category: "Actions"
    },
    {
      id: "new-chat",
      label: "New Chat",
      icon: <MessageSquare className="w-4 h-4" />,
      action: () => router.push("/chat?new=true"),
      shortcut: "N C",
      category: "Actions"
    },
    {
      id: "keyboard",
      label: "Keyboard Shortcuts",
      icon: <Keyboard className="w-4 h-4" />,
      action: () => {},
      shortcut: "?",
      category: "Help"
    },
    {
      id: "start-workflow",
      label: "Start Workflow",
      icon: <Play className="w-4 h-4" />,
      action: () => setOpen(false),
      shortcut: "S W",
      category: "Orchestration"
    },
    {
      id: "stop-workflow",
      label: "Stop Workflow",
      icon: <Square className="w-4 h-4" />,
      action: () => setOpen(false),
      shortcut: "S S",
      category: "Orchestration"
    },
    {
      id: "toggle-focus",
      label: "Toggle Focus Mode",
      icon: <Focus className="w-4 h-4" />,
      action: () => setOpen(false),
      shortcut: "F",
      category: "Orchestration"
    },
    {
      id: "add-task",
      label: "Add Task",
      icon: <ListTodo className="w-4 h-4" />,
      action: () => setOpen(false),
      shortcut: "A T",
      category: "Orchestration"
    },
    {
      id: "clear-completed",
      label: "Clear Completed",
      icon: <CheckCircle2 className="w-4 h-4" />,
      action: () => setOpen(false),
      shortcut: "C C",
      category: "Orchestration"
    },
    {
      id: "toggle-step",
      label: "Toggle Step Mode",
      icon: <Layers className="w-4 h-4" />,
      action: () => setOpen(false),
      shortcut: "T S",
      category: "Orchestration"
    },
    {
      id: "save-workflow",
      label: "Save Workflow",
      icon: <Save className="w-4 h-4" />,
      action: () => setOpen(false),
      shortcut: "S V",
      category: "Orchestration"
    },
    {
      id: "load-workflow",
      label: "Load Workflow",
      icon: <FolderOpen className="w-4 h-4" />,
      action: () => setOpen(false),
      shortcut: "L W",
      category: "Orchestration"
    },
    {
      id: "switch-tasks",
      label: "Switch to Tasks Tab",
      icon: <ListTodo className="w-4 h-4" />,
      action: () => setOpen(false),
      shortcut: "1",
      category: "Tab Navigation"
    },
    {
      id: "switch-nodes",
      label: "Switch to Nodes Tab",
      icon: <GitBranch className="w-4 h-4" />,
      action: () => setOpen(false),
      shortcut: "2",
      category: "Tab Navigation"
    },
    {
      id: "switch-execution",
      label: "Switch to Execution Tab",
      icon: <Play className="w-4 h-4" />,
      action: () => setOpen(false),
      shortcut: "3",
      category: "Tab Navigation"
    },
    {
      id: "switch-agents",
      label: "Switch to Agents Tab",
      icon: <Brain className="w-4 h-4" />,
      action: () => setOpen(false),
      shortcut: "4",
      category: "Tab Navigation"
    },
    {
      id: "switch-policy",
      label: "Switch to Policy Tab",
      icon: <Eye className="w-4 h-4" />,
      action: () => setOpen(false),
      shortcut: "5",
      category: "Tab Navigation"
    },
    {
      id: "switch-templates",
      label: "Switch to Templates Tab",
      icon: <Layers className="w-4 h-4" />,
      action: () => setOpen(false),
      shortcut: "6",
      category: "Tab Navigation"
    },
  ]

  const filteredCommands = query
    ? commands.filter(cmd => 
        cmd.label.toLowerCase().includes(query.toLowerCase()) ||
        cmd.category.toLowerCase().includes(query.toLowerCase())
      )
    : commands

  // Group commands by category
  const groupedCommands = filteredCommands.reduce((acc, cmd) => {
    if (!acc[cmd.category]) {
      acc[cmd.category] = []
    }
    acc[cmd.category].push(cmd)
    return acc
  }, {} as Record<string, CommandItem[]>)

  // Handle keyboard shortcut
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault()
        setOpen(true)
      }
      if (e.key === "Escape") {
        setOpen(false)
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [])

  // Reset selection when query changes
  React.useEffect(() => {
    setSelectedIndex(0)
  }, [query])

  // Handle keyboard navigation in the command palette
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault()
      setSelectedIndex(prev => 
        prev < filteredCommands.length - 1 ? prev + 1 : 0
      )
    } else if (e.key === "ArrowUp") {
      e.preventDefault()
      setSelectedIndex(prev => 
        prev > 0 ? prev - 1 : filteredCommands.length - 1
      )
    } else if (e.key === "Enter") {
      e.preventDefault()
      if (filteredCommands[selectedIndex]) {
        filteredCommands[selectedIndex].action()
        setOpen(false)
        setQuery("")
      }
    }
  }

  return (
    <>
      {/* Hint that appears at the bottom of the screen */}
      <div className="fixed bottom-4 right-4 text-xs text-muted-foreground bg-muted px-2 py-1 rounded border md:hidden" aria-hidden="true">
        Press Ctrl+K for commands
      </div>
      <div className="fixed bottom-4 right-4 hidden md:flex items-center gap-1 text-xs text-muted-foreground bg-muted px-2 py-1 rounded border" aria-hidden="true">
        <kbd className="px-1.5 py-0.5 bg-background rounded border text-[10px]">Ctrl</kbd>
        <span>+</span>
        <kbd className="px-1.5 py-0.5 bg-background rounded border text-[10px]">K</kbd>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="p-0 gap-0 max-w-lg w-[90vw]">
          <div className="flex items-center border-b px-3" cmdk-input-wrapper="">
            <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
            <Input
              className="flex h-11 border-0 bg-transparent px-2 py-3 text-sm outline-none placeholder:text-muted-foreground focus-visible:ring-0"
              placeholder="Search commands..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              autoFocus
              aria-label="Search commands"
            />
          </div>
          <div className="max-h-[300px] overflow-y-auto py-2">
            {filteredCommands.length === 0 ? (
              <div className="py-6 text-center text-sm text-muted-foreground">
                No commands found
              </div>
            ) : (
              Object.entries(groupedCommands).map(([category, items]) => (
                <div key={category} className="mb-2">
                  <div className="px-3 py-1.5 text-xs font-medium text-muted-foreground">
                    {category}
                  </div>
                  {items.map((item, idx) => {
                    const globalIdx = filteredCommands.indexOf(item)
                    return (
                      <button
                        key={item.id}
                        className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-left transition-colors hover:bg-accent hover:text-accent-foreground ${
                          globalIdx === selectedIndex ? "bg-accent text-accent-foreground" : ""
                        }`}
                        onClick={() => {
                          item.action()
                          setOpen(false)
                          setQuery("")
                        }}
                        onMouseEnter={() => setSelectedIndex(globalIdx)}
                        aria-selected={globalIdx === selectedIndex}
                        role="option"
                      >
                        <span className="opacity-50">{item.icon}</span>
                        <span className="flex-1">{item.label}</span>
                        {item.shortcut && (
                          <kbd className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                            {item.shortcut}
                          </kbd>
                        )}
                      </button>
                    )
                  })}
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}