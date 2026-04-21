"use client"

import * as React from "react"
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle,
  CardFooter
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { 
  Bot, 
  Cpu, 
  Download, 
  Upload,
  Terminal,
  FlaskConical,
  FileJson,
  MemoryStick,
  Loader2,
  Play
} from "lucide-react"

export default function TrainerPage() {
  const [inferencePrompt, setInferencePrompt] = React.useState("")
  const [inferenceResult, setInferenceResult] = React.useState<string | null>(null)
  const [isInferring, setIsInferring] = React.useState(false)
  const [models, setModels] = React.useState<{name: string, accuracy: string}[]>([])
  const [tools, setTools] = React.useState<string[]>([])
  const [apiStatus, setApiStatus] = React.useState<"connected" | "disconnected">("disconnected")

  React.useEffect(() => {
    async function initData() {
      try {
        const healthRes = await fetch("http://localhost:8000/health")
        if (healthRes.ok) {
          setApiStatus("connected")
          
          const [modelsRes, toolsRes] = await Promise.all([
            fetch("http://localhost:8000/models"),
            fetch("http://localhost:8000/tools")
          ])
          
          if (modelsRes.ok) {
            const modelsData = await modelsRes.json()
            setModels(modelsData.models || [])
          }
          
          if (toolsRes.ok) {
            const toolsData = await toolsRes.json()
            setTools(toolsData.tools || [])
          }
        }
      } catch {
        setApiStatus("disconnected")
        setModels([
          { name: "rosetta-1.5b-final", accuracy: "100%" },
          { name: "rosetta-1.5b-v36", accuracy: "98%" },
          { name: "rosetta-0.5b-test", accuracy: "85%" },
        ])
        setTools([
          "memory_search", "memory_write", "read", "write",
          "grep", "glob", "git_status", "git_log",
          "github_list_issues", "browser_navigate", "sqlite_query", "lsp_diagnostics",
        ])
      }
    }
    initData()
  }, [])

  const handleInference = async () => {
    if (!inferencePrompt.trim()) return
    
    setIsInferring(true)
    setInferenceResult(null)
    
    try {
      const res = await fetch("http://localhost:8000/inference", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: inferencePrompt })
      })
      
      if (res.ok) {
        const data = await res.json()
        setInferenceResult(JSON.stringify(data, null, 2))
      } else {
        setInferenceResult(`Error: ${res.status} ${res.statusText}`)
      }
    } catch (err) {
      setInferenceResult(`Connection failed: ${err instanceof Error ? err.message : "Unknown error"}`)
    }
    
    setIsInferring(false)
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Bot className="w-8 h-8" />
            Rosetta Trainer
          </h1>
          <p className="text-muted-foreground mt-1">
            Train and run inference with the Rosetta Stone model
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm ${
            apiStatus === "connected" 
              ? "bg-green-500/10 text-green-500" 
              : "bg-red-500/10 text-red-500"
          }`}>
            <span className={`w-2 h-2 rounded-full ${
              apiStatus === "connected" ? "bg-green-500" : "bg-red-500"
            }`} />
            {apiStatus === "connected" ? "API Connected" : "API Offline"}
          </div>
          <Button variant="outline" size="sm">
            <Upload className="w-4 h-4 mr-2" />
            Import Model
          </Button>
          <Button variant="outline" size="sm">
            <Download className="w-4 h-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      <Tabs defaultValue="training" className="space-y-4">
        <TabsList>
          <TabsTrigger value="training" className="gap-2">
            <FlaskConical className="w-4 h-4" />
            Training
          </TabsTrigger>
          <TabsTrigger value="inference" className="gap-2">
            <Terminal className="w-4 h-4" />
            Inference
          </TabsTrigger>
          <TabsTrigger value="models" className="gap-2">
            <Cpu className="w-4 h-4" />
            Models
          </TabsTrigger>
          <TabsTrigger value="tools" className="gap-2">
            <FileJson className="w-4 h-4" />
            Tools
          </TabsTrigger>
        </TabsList>

        <TabsContent value="training" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Training Jobs</CardTitle>
              <CardDescription>Manage and monitor training runs</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center text-muted-foreground py-12">
                <FlaskConical className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p className="text-lg font-medium">No active training jobs</p>
                <p className="text-sm mt-2">Training is managed via CLI. Use the Inference tab to test the model.</p>
              </div>
            </CardContent>
            <CardFooter>
              <Button className="w-full" disabled>
                <Play className="w-4 h-4 mr-2" />
                Start New Training
              </Button>
            </CardFooter>
          </Card>
        </TabsContent>

        <TabsContent value="inference" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Run Inference</CardTitle>
              <CardDescription>
                Test the trained model with natural language prompts
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Input 
                  placeholder="Enter your prompt (e.g., 'search memory for authentication tokens')"
                  value={inferencePrompt}
                  onChange={(e) => setInferencePrompt(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleInference()}
                  className="flex-1"
                />
                <Button 
                  onClick={handleInference}
                  disabled={isInferring || !inferencePrompt.trim()}
                >
                  {isInferring ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <Terminal className="w-4 h-4 mr-2" />
                      Run
                    </>
                  )}
                </Button>
              </div>
              
              {inferenceResult && (
                <div className="rounded-lg border bg-muted p-4">
                  <div className="text-sm font-medium mb-2">Result:</div>
                  <pre className="text-sm font-mono overflow-x-auto">
                    {inferenceResult}
                  </pre>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Quick Examples</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              {[
                "search memory for auth tokens",
                "read file /src/main.py",
                "list all python files",
                "query database",
                "navigate to github.com",
                "create issue for bug",
              ].map((prompt) => (
                <Button
                  key={prompt}
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setInferencePrompt(prompt)
                    setInferenceResult(null)
                  }}
                >
                  {prompt}
                </Button>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="models" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Available Models</CardTitle>
              <CardDescription>Trained LoRA adapters</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {models.length > 0 ? (
                  models.map((model) => (
                    <div key={model.name} className="flex items-center justify-between p-4 rounded-lg border">
                      <div className="flex items-center gap-3">
                        <Cpu className="w-5 h-5 text-muted-foreground" />
                        <div>
                          <div className="font-medium">{model.name}</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge variant="secondary">{model.accuracy} accuracy</Badge>
                        <Button variant="ghost" size="sm">
                          <Download className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center text-muted-foreground py-8">
                    No trained models found. Start training to see models here.
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="tools" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>MCP Tools</CardTitle>
              <CardDescription>Tools available for tool calling</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {tools.length > 0 ? (
                  tools.slice(0, 24).map((tool) => (
                    <Badge key={tool} variant="outline" className="justify-start py-2 px-3">
                      <MemoryStick className="w-3 h-3 mr-2" />
                      {tool}
                    </Badge>
                  ))
                ) : (
                  <div className="col-span-full text-center text-muted-foreground py-8">
                    No tools available
                  </div>
                )}
              </div>
              {tools.length > 24 && (
                <div className="mt-4 text-sm text-muted-foreground">
                  + {tools.length - 24} more tools
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}