import type { Metadata, Viewport } from "next";
import { Outfit } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/providers/query-provider";
import { Navigation } from "@/components/Navigation";
import { Toaster } from "@/components/ui/toaster";

const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "N-Xyme MIND",
    template: "%s | N-Xyme MIND",
  },
  description: "AI coding workspace powered by OpenCode + OMO multi-agent orchestration",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0a0a0a",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={outfit.variable}>
      <body className="antialiased bg-background text-foreground min-h-screen">
        <QueryProvider>
          <Navigation />
          <Toaster />
          <main>{children}</main>
        </QueryProvider>
      </body>
    </html>
  );
}