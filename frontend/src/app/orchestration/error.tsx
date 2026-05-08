"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertTriangle, RefreshCw, GitBranch } from "lucide-react";
import Link from "next/link";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Orchestration error:", error, error.digest);
  }, [error]);

  useEffect(() => {
    fetch('/api/memory/write', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        content: `ERROR: ${error.message}, Stack: ${error.stack}, Digest: ${error.digest}`,
        kind: 'episodic',
        scope: 'session'
      })
    }).catch(e => console.warn('Failed to log error to memory:', e));
  }, [error]);

  return (
    <div className="container mx-auto py-12">
      <Card className="max-w-md mx-auto">
        <CardHeader className="text-center pb-2">
          <div className="mx-auto mb-4">
            <AlertTriangle className="w-12 h-12 text-destructive" />
          </div>
          <CardTitle className="text-2xl">Orchestration Error</CardTitle>
        </CardHeader>
        <CardContent className="text-center space-y-4">
          <p className="text-muted-foreground">
            Unable to load the orchestration view. Please try again.
          </p>
          <div className="flex flex-col gap-2">
            <Button onClick={reset} className="w-full gap-2">
              <RefreshCw className="w-4 h-4" />
              Try Again
            </Button>
            <Button variant="outline" asChild className="w-full gap-2">
              <Link href="/">
                <GitBranch className="w-4 h-4" />
                Go Home
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
