'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Brain, Settings, Zap, Users, MessageSquare } from 'lucide-react';
import { cn } from '@/lib/utils';

const navItems = [
  { href: '/trainer', label: 'Trainer', icon: Zap },
  { href: '/hub', label: 'Hub', icon: Brain },
  { href: '/inference', label: 'Inference', icon: MessageSquare },
  { href: '/team', label: 'Team', icon: Users },
  { href: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside 
      className={cn(
        "flex flex-col border-r transition-all duration-300",
        collapsed ? "w-16" : "w-64"
      )}
      style={{
        backgroundColor: 'var(--color-bg-secondary)',
        borderColor: 'var(--color-border)',
        height: '100vh'
      }}
    >
      <div className="h-16 flex items-center px-4 border-b" style={{ borderColor: 'var(--color-border)' }}>
        <div className="flex items-center gap-3">
          <div 
            className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ backgroundColor: 'var(--color-accent)' }}
          >
            <Zap className="w-5 h-5 text-white" />
          </div>
          {!collapsed && (
            <span className="font-semibold" style={{ color: 'var(--color-text-primary)' }}>N-Xyme</span>
          )}
        </div>
      </div>

      <nav className="flex-1 p-2 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors",
                isActive 
                  ? "bg-accent/10" 
                  : "hover:bg-bg-tertiary"
              )}
              style={{
                color: isActive 
                  ? 'var(--color-accent)' 
                  : 'var(--color-text-secondary)'
              }}
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              {!collapsed && (
                <span className="font-medium" style={{ color: isActive 
                  ? 'var(--color-accent)' 
                  : 'var(--color-text-primary)' }}>{item.label}</span>
              )}
            </Link>
          );
        })}
      </nav>

      <div className="p-2 border-t" style={{ borderColor: 'var(--color-border)' }}>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-center py-2 rounded-lg hover:bg-bg-tertiary"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          {collapsed ? '→' : '← Collapse'}
        </button>
      </div>
    </aside>
  );
}