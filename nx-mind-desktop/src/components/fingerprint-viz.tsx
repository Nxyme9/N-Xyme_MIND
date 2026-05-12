import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { RefreshCw, Brain, Layers, User, Clock } from "lucide-react";

interface FingerprintContext {
  status?: string;
  injected_context?: string;
  scope?: string;
  global_initialized?: boolean;
  cross_session_count?: number;
  tokens_approx?: number;
  components?: {
    memory?: boolean;
    session?: boolean;
    preferences?: boolean;
  };
}

export function FingerprintViz({ agent = "sisyphus", task = "current task" }: { agent?: string; task?: string }) {
  const [context, setContext] = useState<FingerprintContext | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchContext() {
      try {
        const res = await fetch(`/api/fingerprint/context?agent=${agent}&task=${encodeURIComponent(task)}`);
        if (res.ok) {
          const data = await res.json();
          setContext(data);
        }
      } catch {}
      setIsLoading(false);
    }
    fetchContext();
  }, [agent, task]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Fingerprint Context</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">Loading...</div>
        </CardContent>
      </Card>
    );
  }

  const components = context?.components || {};
  const scope = context?.scope || "unknown";

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium">Fingerprint Context</CardTitle>
        <div className="flex items-center gap-2">
          {context?.global_initialized ? (
            <span className="text-xs px-2 py-0.5 rounded-full bg-green-500/20 text-green-400">Active</span>
          ) : (
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-500/20 text-slate-400">Inactive</span>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3 mb-3">
          <div className="flex items-center gap-2">
            <Brain className={`w-4 h-4 ${components.memory ? "text-green-400" : "text-slate-500"}`} />
            <span className="text-xs text-muted-foreground">Memory</span>
            {components.memory && <Badge variant="outline" className="text-[10px] h-5 ml-auto">✓</Badge>}
          </div>
          <div className="flex items-center gap-2">
            <Clock className={`w-4 h-4 ${components.session ? "text-green-400" : "text-slate-500"}`} />
            <span className="text-xs text-muted-foreground">Session</span>
            {components.session && <Badge variant="outline" className="text-[10px] h-5 ml-auto">✓</Badge>}
          </div>
          <div className="flex items-center gap-2">
            <User className={`w-4 h-4 ${components.preferences ? "text-green-400" : "text-slate-500"}`} />
            <span className="text-xs text-muted-foreground">Preferences</span>
            {components.preferences && <Badge variant="outline" className="text-[10px] h-5 ml-auto">✓</Badge>}
          </div>
          <div className="flex items-center gap-2">
            <Layers className={`w-4 h-4 ${context?.global_initialized ? "text-green-400" : "text-slate-500"}`} />
            <span className="text-xs text-muted-foreground">Global</span>
            {context?.global_initialized && <Badge variant="outline" className="text-[10px] h-5 ml-auto">✓</Badge>}
          </div>
        </div>
        <div className="flex items-center justify-between text-xs text-muted-foreground pt-2 border-t">
          <span>Scope: {scope}</span>
          <span>{context?.tokens_approx || 0} tokens</span>
        </div>
        {context?.cross_session_count !== undefined && context?.cross_session_count > 0 && (
          <div className="text-xs text-muted-foreground mt-1">
            {context.cross_session_count} cross-session memories
          </div>
        )}
      </CardContent>
    </Card>
  );
}