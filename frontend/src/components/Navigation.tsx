"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { 
  Bot, 
  LayoutDashboard, 
  GitBranch, 
  Brain, 
  MessageSquare, 
  Settings, 
  Menu, 
  X,
  GraduationCap 
} from "lucide-react"

interface NavLink {
  href: string
  icon: React.ComponentType<{ className?: string }>
  label: string
  aria: string
}

const navLinks: NavLink[] = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard", aria: "Go to Dashboard" },
  { href: "/orchestration", icon: GitBranch, label: "Orchestration", aria: "Go to Orchestration" },
  { href: "/memory", icon: Brain, label: "Memory", aria: "Go to Memory" },
  { href: "/trainer", icon: GraduationCap, label: "Trainer", aria: "Go to Rosetta Trainer" },
  { href: "/chat", icon: MessageSquare, label: "Chat", aria: "Go to Chat" },
  { href: "/settings", icon: Settings, label: "Settings", aria: "Go to Settings" },
]

function NavLinkItem({ href, icon: Icon, label, aria }: NavLinkItemProps) {
  const pathname = usePathname()
  const isActive = pathname === href || (href !== "/" && pathname.startsWith(href))
  
  return (
    <Link 
      href={href}
      className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition-all duration-200 whitespace-nowrap group relative overflow-hidden ${
        isActive 
          ? "bg-primary/20 text-primary neon-glow" 
          : "hover:bg-muted/50 hover:text-primary/80"
      }`}
      aria-label={aria}
      aria-current={isActive ? "page" : undefined}
    >
      <Icon className={`w-4 h-4 transition-transform duration-200 group-hover:scale-110 ${isActive ? "text-primary" : ""}`} aria-hidden="true" />
      <span className="hidden sm:inline relative z-10">{label}</span>
      {isActive && (
        <span className="absolute inset-0 bg-gradient-to-r from-primary/10 to-transparent animate-pulse-glow rounded-md" />
      )}
    </Link>
  )
}

interface NavLinkItemProps {
  href: string
  icon: React.ComponentType<{ className?: string }>
  label: string
  aria: string
}

export function Navigation() {
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false)

  return (
    <nav className="border-b bg-card" role="navigation" aria-label="Main navigation">
      <div className="container mx-auto flex items-center gap-4 px-4 py-3">
        <Link href="/" className="flex items-center gap-2 font-semibold shrink-0">
          <Bot className="w-6 h-6" aria-hidden="true" />
          <span className="whitespace-nowrap">N-Xyme MIND</span>
        </Link>
        
        {/* Desktop navigation */}
        <div className="hidden md:flex items-center gap-1 overflow-x-auto">
          {navLinks.map((link) => (
            <NavLinkItem key={link.href} {...link} />
          ))}
        </div>

        {/* Mobile menu button */}
        <button
          className="md:hidden ml-auto p-2 rounded-md hover:bg-muted transition-colors focus:outline-none focus:ring-2 focus:ring-ring"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-expanded={mobileMenuOpen}
          aria-controls="mobile-menu"
          aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
        >
          {mobileMenuOpen ? (
            <X className="w-5 h-5" aria-hidden="true" />
          ) : (
            <Menu className="w-5 h-5" aria-hidden="true" />
          )}
        </button>
      </div>

      {/* Mobile menu dropdown */}
      {mobileMenuOpen && (
        <div 
          id="mobile-menu"
          className="md:hidden border-t px-4 py-3 bg-card"
          role="menu"
          aria-label="Mobile navigation"
        >
          <div className="flex flex-col gap-1">
            {navLinks.map((link) => (
              <Link 
                key={link.href}
                href={link.href}
                className="flex items-center gap-3 px-3 py-2 rounded-md text-sm hover:bg-muted transition-colors"
                role="menuitem"
                aria-label={link.aria}
                onClick={() => setMobileMenuOpen(false)}
              >
                <link.icon className="w-4 h-4" aria-hidden="true" />
                <span>{link.label}</span>
              </Link>
            ))}
          </div>
        </div>
      )}
    </nav>
  )
}