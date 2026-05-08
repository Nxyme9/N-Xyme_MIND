import type { Metadata, Viewport } from "next";
import { JetBrains_Mono, Outfit } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/providers/query-provider";
import { AuthProvider } from "@/components/auth-provider";
import { ErrorBoundary } from "@/components/error-boundary";
import { CommandPalette } from "@/components/command-palette";
import { ToastProvider } from "@/context/ToastContext";
import { ToastContainer } from "@/components/Toast";
import { Toaster } from "@/components/ui/toaster";
import { Navigation } from "@/components/Navigation";
import { GlobalLoadingOverlay } from "@/components/GlobalLoadingOverlay";
import { NetworkStatus } from "@/components/NetworkStatus";
import { FloatingQuickActions } from "@/components/ui/floating-quick-actions";
import { CognitiveStateProvider } from "@/providers/cognitive-state-provider";
import { FocusShieldProvider, FocusShieldNotification } from "@/components/focus-shield";

const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "N-Xyme MIND",
    template: "%s | N-Xyme MIND",
  },
  description: "AI coding workspace powered by OpenCode + OMO multi-agent orchestration",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "N-Xyme MIND",
  },
  openGraph: {
    title: "N-Xyme MIND",
    description: "AI coding workspace powered by OpenCode + OMO multi-agent orchestration",
    type: "website",
    locale: "en_US",
    siteName: "N-Xyme MIND",
  },
  twitter: {
    card: "summary_large_image",
    title: "N-Xyme MIND",
    description: "AI coding workspace powered by OpenCode + OMO multi-agent orchestration",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${outfit.variable} ${jetbrainsMono.variable} min-h-screen bg-background text-foreground`}
      >
        {/* Skip to content link for accessibility */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-md"
        >
          Skip to content
        </a>
        <ErrorBoundary>
          <AuthProvider>
            <ToastProvider>
              <QueryProvider>
                <CognitiveStateProvider>
                <FocusShieldProvider>
                  <GlobalLoadingOverlay />
                  <NetworkStatus />
                  <Navigation />
                  <main id="main-content">
                    <CommandPalette />
                    <FloatingQuickActions />
                    <Toaster />
                    <ToastContainer />
                    <FocusShieldNotification />
                    {children}
                  </main>
                </FocusShieldProvider>
              </CognitiveStateProvider>
              </QueryProvider>
            </ToastProvider>
          </AuthProvider>
        </ErrorBoundary>
      </body>
    </html>
  );
}