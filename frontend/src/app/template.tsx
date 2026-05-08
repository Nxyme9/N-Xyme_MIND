"use client";

import { PageTransition, StaggerContainer, StaggerItem } from "@/components/ui/page-transition";

export { PageTransition, StaggerContainer, StaggerItem };

export default function Template({ children }: { children: React.ReactNode }) {
  return <PageTransition>{children}</PageTransition>;
}