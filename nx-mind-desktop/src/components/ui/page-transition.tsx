"use client";

import { usePathname } from "next/navigation";
import { ReactNode } from "react";

interface PageTransitionProps {
  children: ReactNode;
}

export function PageTransition({ children }: PageTransitionProps) {
  const pathname = usePathname();

  return (
    <div
      className="page-transition-container animate-page-enter"
      key={pathname}
    >
      {children}
    </div>
  );
}

export function StaggerContainer({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`stagger-children ${className}`}>{children}</div>;
}

export function StaggerItem({ children, delay = 0 }: { children: ReactNode; delay?: number }) {
  return (
    <div
      className="stagger-item"
      style={{ animationDelay: `${delay}ms` }}
    >
      {children}
    </div>
  );
}