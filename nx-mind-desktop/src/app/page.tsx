"use client";

import { useSystemStatus } from "@/hooks/useSystemStatus";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
   LayoutDashboard, 
   GitBranch, 
   Brain, 
   MessageSquare,
   Bot,
   Activity,
   Zap,
   Clock,
   ArrowRight
} from "lucide-react";
import Link from "next/link";
import DictateUI from "@/components/dictate/DictateUI";

export default function Home() {
  const { isConnected, connectionLabel, isLoading } = useSystemStatus();

  return (
    <div className="container mx-auto py-12">
      {/* Hero Section */}
      <div className="text-center mb-12">
        <div className="flex items-center justify-center gap-3 mb-4">
          <div className="p-3 bg-primary/10 rounded-full">
            <Bot className="w-10 h-10 text-primary" />
          </div>
        </div>
        <h1 className="text-4xl font-bold mb-2">N-Xyme MIND</h1>
        <p className="text-xl text-muted-foreground mb-4">
          AI Coding Workspace — OpenCode + OMO Multi-Agent Orchestration
        </p>
        <Badge 
          variant={isConnected ? "default" : "destructive"}
          className={isConnected ? "bg-green-500 border-0" : "bg-red-500 border-0"}
        >
          {isLoading ? "Connecting..." : connectionLabel}
        </Badge>
      </div>

      {/* Dictate Feature - Prominent ADHD-friendly voice interface */}
      <div className="mb-12">
        <Card className="hover:border-primary/50 transition-colors cursor-pointer group h-full">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <Bot className="w-6 h-6 text-primary" />
              <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
            <CardTitle className="text-lg">Dictate</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              GPU-accelerated live dictation with ADHD-friendly visual feedback
            </p>
            <DictateUI />
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions - ADHD Friendly */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-12">
        <Link href="/dashboard">
          <Card className="hover:border-primary/50 transition-colors cursor-pointer group h-full">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <LayoutDashboard className="w-6 h-6 text-blue-500" />
                <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <CardTitle className="text-lg">Dashboard</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Agent status, MCP connections, task queue
              </p>
            </CardContent>
          </Card>
        </Link>
         
        <Link href="/orchestration">
          <Card className="hover:border-primary/50 transition-colors cursor-pointer group h-full">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <GitBranch className="w-6 h-6 text-purple-500" />
                <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <CardTitle className="text-lg">Orchestration</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Task flow visualization, agent workloads
              </p>
            </CardContent>
          </Card>
        </Link>
         
        <Link href="/memory">
          <Card className="hover:border-primary/50 transition-colors cursor-pointer group h-full">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <Brain className="w-6 h-6 text-green-500" />
                <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <CardTitle className="text-lg">Memory</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Semantic & episodic memories, context search
              </p>
            </CardContent>
          </Card>
        </Link>
         
        <Link href="/chat">
          <Card className="hover:border-primary/50 transition-colors cursor-pointer group h-full">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <MessageSquare className="w-6 h-6 text-orange-500" />
                <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <CardTitle className="text-lg">Chat</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                AI chat with streaming responses
              </p>
            </CardContent>
          </Card>
        </Link>
      </div>

      {/* Features Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-blue-500" />
              <CardTitle className="text-base">Real-time Status</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Live monitoring of all agents, MCP connections, and system health with auto-refresh.
            </p>
          </CardContent>
        </Card>
         
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Zap className="w-5 h-5 text-yellow-500" />
              <CardTitle className="text-base">Smart Routing</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Adaptive task routing with Q-Learning that improves over time based on outcomes.
            </p>
          </CardContent>
        </Card>
         
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-green-500" />
              <CardTitle className="text-base">Memory System</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Unified memory across sessions with semantic search, episodic recall, and context finding.
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Keyboard Shortcuts Info */}
      <div className="mt-12 p-4 bg-muted/50 rounded-lg">
        <h3 className="font-semibold mb-2">Keyboard Shortcuts (ADHD-Friendly)</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
          <div><kbd className="px-2 py-1 bg-background rounded text-xs">Ctrl+K</kbd> Command Palette</div>
          <div><kbd className="px-2 py-1 bg-background rounded text-xs">G D</kbd> Dashboard</div>
          <div><kbd className="px-2 py-1 bg-background rounded text-xs">G O</kbd> Orchestration</div>
          <div><kbd className="px-2 py-1 bg-background rounded text-xs">G M</kbd> Memory</div>
          <div><kbd className="px-2 py-1 bg-background rounded text-xs">G C</kbd> Chat</div>
          <div><kbd className="px-2 py-1 bg-background rounded text-xs">?</kbd> Shortcuts Help</div>
        </div>
      </div>
    </div>
  );
}