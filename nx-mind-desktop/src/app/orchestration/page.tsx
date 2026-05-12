"use client";

import { useCallback, useState, useEffect, useRef } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  addEdge,
  useNodesState,
  useEdgesState,
  Connection,
  MarkerType,
  Panel,
  BackgroundVariant,
  NodeTypes,
  useReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import {
  Settings, 
  Plus, 
  Trash2, 
  RefreshCw, 
  Zap, 
  Brain, 
  Code2, 
  Search,
  BookOpen,
  Eye,
  Target,
  Play,
  Pause,
  Square,
  Save,
  RotateCcw,
  Pencil,
  Upload,
  Download,
  Calendar,
  X,
  Check,
  Wifi,
  WifiOff,
  ZoomIn,
  Maximize2,
  Map,
  MapPin,
  FileText,
  ChevronUp,
  ChevronDown,
  SkipForward,
  Clock,
  FileUp,
  FileDown,
  GripVertical,
  Link2,
  Link2Off,
  ArrowRight,
  AlertTriangle,
  GitBranch,
  Layers,
  Sparkles,
  Wrench,
  Workflow,
  Shield,
} from "lucide-react";

// dnd-kit imports
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { useAgentStore, type Agent } from "@/stores/useAgentStore";
import { useTaskStore, type Task } from "@/stores/useTaskStore";
import { useSessionState, useOrchestrationTools, useTaskStatus, useSpawnAgent, useCatalystState } from "@/hooks/useOrchestration";

interface AgentConfig {
  id: string;
  name: string;
  role: string;
  enabled: boolean;
  color: string;
  icon: React.ReactNode;
  timeout: number;
  maxRetries: number;
  capacity: number;
  model: string;
}

const mapBackendAgentToConfig = (backendAgent: { id: string; name: string; status?: string }): AgentConfig => {
  const roleMap: Record<string, string> = {
    sisyphus: "Master Orchestrator",
    hephaestus: "Implementation",
    oracle: "Architecture Review",
    explore: "Codebase Search",
    librarian: "External Research",
    prometheus: "Plan Builder",
    momus: "Adversarial Review",
    atlas: "Plan Executor",
    metis: "Pre-planning",
  };
  
  const colorMap: Record<string, string> = {
    sisyphus: "#f59e0b",
    hephaestus: "#22c55e",
    oracle: "#3b82f6",
    explore: "#06b6d4",
    librarian: "#84cc16",
    prometheus: "#8b5cf6",
    momus: "#ef4444",
    atlas: "#f97316",
    metis: "#ec4899",
  };
  
  const modelMap: Record<string, string> = {
    sisyphus: "minimax-m2.5-free",
    hephaestus: "GPT-4o",
    oracle: "Claude 3.5 Sonnet",
    explore: "GPT-4o",
    librarian: "Claude 3.5 Sonnet",
    prometheus: "GPT-4o",
    momus: "Gemini 1.5 Pro",
    atlas: "GPT-4o",
    metis: "GPT-4o",
  };
  
  return {
    id: backendAgent.id,
    name: backendAgent.name,
    role: roleMap[backendAgent.id] || "Agent",
    enabled: true,
    color: colorMap[backendAgent.id] || "#6b7280",
    icon: <Brain className="w-4 h-4" />,
    timeout: 300,
    maxRetries: 3,
    capacity: 10,
    model: modelMap[backendAgent.id] || "GPT-4o",
  };
};

const DEFAULT_AGENTS: AgentConfig[] = [
  { id: "hephaestus", name: "Hephaestus", role: "Implementation", enabled: true, color: "#22c55e", icon: <Code2 className="w-4 h-4" />, timeout: 300, maxRetries: 3, capacity: 10, model: "GPT-4o" },
  { id: "oracle", name: "Oracle", role: "Architecture Review", enabled: true, color: "#3b82f6", icon: <Eye className="w-4 h-4" />, timeout: 300, maxRetries: 3, capacity: 10, model: "Claude 3.5 Sonnet" },
  { id: "explore", name: "Explore", role: "Codebase Search", enabled: true, color: "#06b6d4", icon: <Search className="w-4 h-4" />, timeout: 300, maxRetries: 3, capacity: 10, model: "GPT-4o" },
  { id: "librarian", name: "Librarian", role: "External Research", enabled: true, color: "#84cc16", icon: <BookOpen className="w-4 h-4" />, timeout: 300, maxRetries: 3, capacity: 10, model: "Claude 3.5 Sonnet" },
  { id: "prometheus", name: "Prometheus", role: "Plan Builder", enabled: true, color: "#8b5cf6", icon: <Target className="w-4 h-4" />, timeout: 300, maxRetries: 3, capacity: 10, model: "GPT-4o" },
  { id: "momus", name: "Momus", role: "Adversarial Review", enabled: true, color: "#ef4444", icon: <Eye className="w-4 h-4" />, timeout: 300, maxRetries: 3, capacity: 10, model: "Gemini 1.5 Pro" },
  { id: "atlas", name: "Atlas", role: "Plan Executor", enabled: true, color: "#f97316", icon: <Target className="w-4 h-4" />, timeout: 300, maxRetries: 3, capacity: 10, model: "GPT-4o" },
];

// Color options for agents
const COLOR_OPTIONS = ["#ef4444", "#f97316", "#f59e0b", "#22c55e", "#3b82f6", "#8b5cf6"];



// Custom styled nodes
const nodeStyles = {
  source: {
    background: "#1e293b",
    border: "2px solid #3b82f6",
    borderRadius: "12px",
    padding: "16px",
    color: "#f8fafc",
    minWidth: "140px",
  },
  orchestrator: {
    background: "#1e293b",
    border: "2px solid #f59e0b",
    borderRadius: "12px",
    padding: "16px",
    color: "#f8fafc",
    minWidth: "140px",
  },
  agent: {
    background: "#1e293b",
    border: "2px solid #22c55e",
    borderRadius: "12px",
    padding: "16px",
    color: "#f8fafc",
    minWidth: "140px",
  },
  router: {
    background: "#1e293b",
    border: "2px solid #ec4899",
    borderRadius: "12px",
    padding: "16px",
    color: "#f8fafc",
    minWidth: "160px",
  },
  splitter: {
    background: "#1e293b",
    border: "2px solid #f97316",
    borderRadius: "12px",
    padding: "16px",
    color: "#f8fafc",
    minWidth: "140px",
  },
  aggregator: {
    background: "#1e293b",
    border: "2px solid #14b8a6",
    borderRadius: "12px",
    padding: "16px",
    color: "#f8fafc",
    minWidth: "140px",
  },
  llm: {
    background: "#1e293b",
    border: "2px solid #a855f7",
    borderRadius: "12px",
    padding: "16px",
    color: "#f8fafc",
    minWidth: "140px",
  },
  tool: {
    background: "#1e293b",
    border: "2px solid #0ea5e9",
    borderRadius: "12px",
    padding: "16px",
    color: "#f8fafc",
    minWidth: "140px",
  },
  subflow: {
    background: "#1e293b",
    border: "2px solid #6366f1",
    borderRadius: "12px",
    padding: "16px",
    color: "#f8fafc",
    minWidth: "140px",
  },
  delegate: {
    background: "#1e293b",
    border: "2px solid #8b5cf6",
    borderRadius: "12px",
    padding: "12px",
    color: "#f8fafc",
    minWidth: "120px",
  },
  output: {
    background: "#1e293b",
    border: "2px solid #06b6d4",
    borderRadius: "12px",
    padding: "16px",
    color: "#f8fafc",
    minWidth: "140px",
  },
};

const nodeIcons: Record<string, React.ReactNode> = {
  agent: <Code2 className="w-4 h-4" />,
  router: <GitBranch className="w-4 h-4" />,
  splitter: <ArrowRight className="w-4 h-4" />,
  aggregator: <Layers className="w-4 h-4" />,
  llm: <Sparkles className="w-4 h-4" />,
  tool: <Wrench className="w-4 h-4" />,
  subflow: <Workflow className="w-4 h-4" />,
};

// Custom node component with better styling
function StyledNode({ data }: { data: { label: string; status?: string; subtitle?: string; type?: string } }) {
  const style = nodeStyles[data.type as keyof typeof nodeStyles] || nodeStyles.agent;
  const icon = nodeIcons[data.type as keyof typeof nodeIcons] || nodeIcons.agent;
  
  const getStatusIndicator = () => {
    switch (data.status) {
      case "working":
      case "running":
        return <div className="w-2.5 h-2.5 rounded-full bg-yellow-400 animate-pulse" />;
      case "completed":
        return <div className="w-2.5 h-2.5 rounded-full bg-green-400" />;
      case "failed":
        return <div className="w-2.5 h-2.5 rounded-full bg-red-400" />;
      default:
        return <div className="w-2.5 h-2.5 rounded-full bg-slate-500" />;
    }
  };

  return (
    <div className="text-center" style={style}>
      <div className="flex items-center justify-center gap-2 mb-2">
        <span style={{ color: style.border.split(" ")[2] }}>{icon}</span>
        {getStatusIndicator()}
        <div className="font-bold text-sm">{data.label}</div>
      </div>
      {data.subtitle && (
        <div className="text-xs text-slate-400">{data.subtitle}</div>
      )}
      {data.status && data.status !== "idle" && (
        <div className="mt-2">
          <Badge 
            variant="outline" 
            className={`text-[10px] ${
              data.status === "working" || data.status === "running" 
                ? "border-yellow-500 text-yellow-400" 
                : data.status === "completed"
                ? "border-green-500 text-green-400"
                : "border-slate-500 text-slate-400"
            }`}
          >
            {data.status}
          </Badge>
        </div>
      )}
    </div>
  );
}

// Register custom node types
const nodeTypes: NodeTypes = {
  styledNode: StyledNode,
};

// Sortable task item component
interface SortableTaskItemProps {
  task: Task;
  onEdit: (task: Task) => void;
  onDelete: (task: Task) => void;
  onAddDependency: (taskId: string, dependsOnId: string) => void;
  onRemoveDependency: (taskId: string, dependsOnId: string) => void;
  allTasks: Task[];
  isLinking: boolean;
  linkingTaskId: string | null;
  onStartLink: (taskId: string) => void;
  onCancelLink: () => void;
  compactMode?: boolean;
  expandedTaskId?: string | null;
  onToggleExpand?: (taskId: string) => void;
}

function SortableTaskItem({ 
  task, 
  onEdit, 
  onDelete, 
  onAddDependency, 
  onRemoveDependency,
  allTasks,
  isLinking,
  linkingTaskId,
  onStartLink,
  onCancelLink,
  compactMode = false,
  expandedTaskId = null,
  onToggleExpand,
}: SortableTaskItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: task.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "urgent": return "text-red-400 border-red-500/50";
      case "high": return "text-orange-400 border-orange-500/50";
      case "medium": return "text-yellow-400 border-yellow-500/50";
      default: return "text-slate-400 border-slate-500/50";
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "running": return "bg-yellow-500/20 border-yellow-500 border-l-4 border-l-yellow-400 animate-pulse";
      case "completed": return "bg-green-500/20 border-green-500 shadow-[0_0_8px_rgba(34,197,94,0.3)]";
      case "failed": return "bg-red-500/20 border-red-500 shadow-[0_0_8px_rgba(239,68,68,0.3)]";
      default: return "bg-slate-800/50 border-slate-600";
    }
  };

  const isExpanded = expandedTaskId === task.id;
  const truncatedDesc = task.description.length > 50 ? task.description.slice(0, 50) + "..." : task.description;
  const createdDate = task.createdAt ? new Date(task.createdAt).toLocaleDateString() : "N/A";
  const dependentTasks = allTasks.filter(t => task.dependsOn?.includes(t.id));

  if (compactMode) {
    return (
      <div
        ref={setNodeRef}
        style={style}
        className={`flex items-center gap-2 p-2 rounded-lg border ${getStatusColor(task.status)} ${isDragging ? "opacity-50 shadow-lg ring-2 ring-blue-500" : ""} relative`}
      >
        <button
          className="cursor-grab active:cursor-grabbing text-slate-400 hover:text-slate-200"
          {...attributes}
          {...listeners}
        >
          <GripVertical className="w-3 h-3" />
        </button>
        <div 
          className="flex-1 min-w-0 cursor-pointer"
          onClick={() => onToggleExpand?.(task.id)}
        >
          <div className="text-xs truncate">{truncatedDesc}</div>
          <div className="flex items-center gap-1 mt-0.5">
            <Badge variant="outline" className={`text-[9px] py-0 px-1 ${getPriorityColor(task.priority)}`}>
              {task.priority}
            </Badge>
            <span className="text-[10px] text-slate-500 capitalize">{task.status}</span>
          </div>
        </div>
        {isExpanded && (
          <div className="absolute left-0 right-0 top-full mt-1 p-3 bg-slate-800 border border-slate-600 rounded-lg z-10 shadow-xl">
            <div className="text-sm mb-2 break-words">{task.description}</div>
            <div className="flex flex-wrap gap-1 mb-2">
              {task.dependsOn && task.dependsOn.length > 0 && (
                <Badge variant="outline" className="text-[10px] bg-blue-500/20 border-blue-500 text-blue-400">
                  <Link2 className="w-2.5 h-2.5 mr-1" />
                  {task.dependsOn.length} dep{task.dependsOn.length === 1 ? '' : 's'}
                </Badge>
              )}
              <span className="text-xs text-slate-500">{createdDate}</span>
            </div>
            <div className="flex items-center gap-1">
              {isLinking ? (
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="h-6"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (linkingTaskId) {
                      onAddDependency(task.id, linkingTaskId);
                    }
                  }}
                  disabled={!linkingTaskId || task.id === linkingTaskId}
                >
                  <Link2 className="w-3 h-3 text-blue-400" />
                </Button>
              ) : (
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="h-6"
                  onClick={() => onStartLink(task.id)}
                >
                  <Link2 className="w-3 h-3" />
                </Button>
              )}
              <Button variant="ghost" size="sm" className="h-6" onClick={() => onEdit(task)}>
                <Pencil className="w-3 h-3" />
              </Button>
              <Button variant="ghost" size="sm" className="h-6" onClick={() => onDelete(task)}>
                <Trash2 className="w-3 h-3" />
              </Button>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`flex items-center gap-3 p-3 rounded-lg border ${getStatusColor(task.status)} ${isDragging ? "opacity-50 shadow-lg ring-2 ring-blue-500" : ""}`}
    >
      <button
        className="cursor-grab active:cursor-grabbing text-slate-400 hover:text-slate-200"
        {...attributes}
        {...listeners}
      >
        <GripVertical className="w-4 h-4" />
      </button>
      <div className="flex-1 min-w-0">
        <div className="text-sm truncate">{task.description}</div>
        <div className="flex items-center gap-2 mt-1">
          <Badge variant="outline" className={`text-[10px] ${getPriorityColor(task.priority)}`}>
            {task.priority}
          </Badge>
          <span className="text-xs text-slate-500 capitalize">{task.status}</span>
          {task.dependsOn && task.dependsOn.length > 0 && (
            <Badge variant="outline" className="text-[10px] bg-blue-500/20 border-blue-500 text-blue-400">
              <Link2 className="w-2.5 h-2.5 mr-1" />
              {task.dependsOn.length} dep{task.dependsOn.length === 1 ? '' : 's'}
            </Badge>
          )}
        </div>
      </div>
      <div className="flex items-center gap-1">
        {/* Link button for creating dependencies */}
        {isLinking ? (
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={(e) => {
              e.stopPropagation();
              if (linkingTaskId) {
                onAddDependency(task.id, linkingTaskId);
              }
            }}
            disabled={!linkingTaskId || task.id === linkingTaskId}
            title="Link to selected task"
          >
            <Link2 className="w-3 h-3 text-blue-400" />
          </Button>
        ) : (
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={() => onStartLink(task.id)}
            title="Create dependency"
          >
            <Link2 className="w-3 h-3" />
          </Button>
        )}
        <Button variant="ghost" size="sm" onClick={() => onEdit(task)}>
          <Pencil className="w-3 h-3" />
        </Button>
        <Button variant="ghost" size="sm" onClick={() => onDelete(task)}>
          <Trash2 className="w-3 h-3" />
        </Button>
      </div>
    </div>
  );
}

// Generate initial nodes based on enabled agents
function generateInitialNodes(agents: AgentConfig[]): Node[] {
  const enabledAgents = agents.filter(a => a.enabled);
  const centerX = 400;
  const startY = 80;
  const verticalSpacing = 140;
  
  const nodes: Node[] = [
    {
      id: "user",
      position: { x: centerX - 70, y: startY },
      data: { label: "USER", status: "idle", type: "source", subtitle: "Input" },
      type: "styledNode",
    },
  ];

  // Sisyphus as main orchestrator
  const sisyphus = enabledAgents.find(a => a.id === "sisyphus");
  if (sisyphus) {
    nodes.push({
      id: "sisyphus",
      position: { x: centerX - 70, y: startY + verticalSpacing },
      data: { label: sisyphus.name, status: "working", subtitle: sisyphus.role, type: "orchestrator" },
      type: "styledNode",
    });
  }

  // Add other enabled agents in a branch pattern
  const otherAgents = enabledAgents.filter(a => a.id !== "sisyphus").slice(0, 4);
  otherAgents.forEach((agent, idx) => {
    const xOffset = idx % 2 === 0 ? -120 : 120;
    nodes.push({
      id: agent.id,
      position: { x: centerX + xOffset - 70, y: startY + verticalSpacing * 2 },
      data: { label: agent.name, status: "idle", subtitle: agent.role, type: "agent" },
      type: "styledNode",
    });
  });

  // Output node
  nodes.push({
    id: "result",
    position: { x: centerX - 70, y: startY + verticalSpacing * 3 },
    data: { label: "RESULT", status: "completed", type: "output", subtitle: "Output" },
    type: "styledNode",
  });

  return nodes;
}

// Generate edges based on enabled agents
function generateInitialEdges(agents: AgentConfig[]): Edge[] {
  const enabledAgents = agents.filter(a => a.enabled);
  const edges: Edge[] = [
    {
      id: "e-user-sisyphus",
      source: "user",
      target: "sisyphus",
      animated: true,
      label: "Task",
      style: { stroke: "#3b82f6", strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: "#3b82f6" },
    },
  ];

  const sisyphus = enabledAgents.find(a => a.id === "sisyphus");
  if (sisyphus) {
    const otherAgents = enabledAgents.filter(a => a.id !== "sisyphus").slice(0, 4);
    otherAgents.forEach((agent, idx) => {
      edges.push({
        id: `e-sisyphus-${agent.id}`,
        source: "sisyphus",
        target: agent.id,
        animated: idx === 0,
        label: idx === 0 ? "Delegate" : "",
        style: { stroke: agent.color, strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: agent.color },
      });
      edges.push({
        id: `e-${agent.id}-result`,
        source: agent.id,
        target: "result",
        animated: false,
        style: { stroke: "#06b6d4", strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: "#06b6d4" },
      });
    });
  }

  return edges;
}

function OrchestrationPageInner() {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const agents = useAgentStore((state) => state.agents);
  const tasks = useTaskStore((state) => state.tasks);
  const updateTask = useTaskStore((state) => state.updateTask);
  const removeTask = useTaskStore((state) => state.removeTask);
  const reorderTasks = useTaskStore((state) => state.reorderTasks);
  const setTasks = useTaskStore((state) => state.setTasks);
  const [newTask, setNewTask] = useState("");
  const [newTaskPriority, setNewTaskPriority] = useState<"low" | "medium" | "high" | "urgent">("medium");
  const [agentConfigs, setAgentConfigs] = useState<AgentConfig[]>(DEFAULT_AGENTS);
  const [activeAgents, setActiveAgents] = useState<AgentConfig[]>(DEFAULT_AGENTS);
  const [isConfigMode, setIsConfigMode] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  
  // Real session state from API hooks - must be called before using session
  const { session, isLoading: sessionLoading } = useSessionState();
  const { tools } = useOrchestrationTools();
  const { state: catalystState, confidence: catalystConfidence } = useCatalystState();
  
  const [backendAgents, setBackendAgents] = useState<AgentConfig[]>([]);
  const [backendAvailable, setBackendAvailable] = useState(false);
  
  useEffect(() => {
    async function fetchBackendAgents() {
      try {
        const response = await fetch("/api/backend/agents");
        if (response.ok) {
          const data = await response.json();
          if (data.agents && Array.isArray(data.agents)) {
            const mapped = data.agents.map(mapBackendAgentToConfig);
            setBackendAgents(mapped);
            setBackendAvailable(data.backendAvailable || false);
          }
        }
      } catch (error) {
        console.error("Failed to fetch backend agents:", error);
        setBackendAvailable(false);
      }
    }
    fetchBackendAgents();
  }, []);
  
  const effectiveAgents = backendAvailable && backendAgents.length > 0 ? backendAgents : DEFAULT_AGENTS;
  
  useEffect(() => {
    setAgentConfigs(effectiveAgents);
    setActiveAgents(effectiveAgents);
  }, [effectiveAgents]);
  
  // WebSocket connection - real session state from API
  const wsConnected = session !== undefined && !sessionLoading;
  const [selectedNodes, setSelectedNodes] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  
  // Modal states
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [deletingTask, setDeletingTask] = useState<Task | null>(null);
  const [clearingCompleted, setClearingCompleted] = useState(false);
  
  // Dependency linking state
  const [isLinking, setIsLinking] = useState(false);
  const [linkingTaskId, setLinkingTaskId] = useState<string | null>(null);
  
  // Task store actions
  const addDependency = useTaskStore((state) => state.addDependency);
  const clearCompleted = useTaskStore((state) => state.clearCompleted);
  const getDependents = useTaskStore((state) => state.getDependents);
  
  // History for undo/redo
  const historyRef = useRef<Node[][]>([]);
  const historyIndexRef = useRef(-1);
  const [editDescription, setEditDescription] = useState("");

  // New visualization and execution state
  const { fitView } = useReactFlow();
  const [showEdgeLabels, setShowEdgeLabels] = useState(true);
  const [showMinimap, setShowMinimap] = useState(true);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [showLogs, setShowLogs] = useState(false);
  const [stepMode, setStepMode] = useState(false);
  const [focusMode, setFocusMode] = useState(false);
  const [compactMode, setCompactMode] = useState(false);
  const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null);
  const [selectedNodeDetails, setSelectedNodeDetails] = useState<Node | null>(null);
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [executionStartTime, setExecutionStartTime] = useState<number | null>(null);
  
  interface GlobalPolicy {
    id: string;
    name: string;
    enabled: boolean;
    trigger: string;
    action: string;
    priority: 'low' | 'medium' | 'high';
    conditions: string[];
  }
  
  const [globalPolicies, setGlobalPolicies] = useState<GlobalPolicy[]>([
    { id: "p1", name: "Block High Cost Tasks", enabled: true, trigger: "on_high_cost", action: "block", priority: "high", conditions: [] },
    { id: "p2", name: "Auto Retry on Timeout", enabled: true, trigger: "on_timeout", action: "retry", priority: "medium", conditions: [] },
    { id: "p3", name: "Fallback on Error", enabled: false, trigger: "on_error", action: "fallback", priority: "low", conditions: [] },
  ]);
  
  interface WorkflowTemplate {
    id: string;
    name: string;
    description: string;
    color: string;
    icon: React.ReactNode;
    tags: string[];
    nodes: Node[];
    edges?: Edge[];
  }
  
  const WORKFLOW_TEMPLATES: WorkflowTemplate[] = [
    {
      id: "sequential",
      name: "Sequential Pipeline",
      description: "Linear task execution with dependencies",
      color: "#3b82f6",
      icon: <ArrowRight className="w-4 h-4" />,
      tags: ["linear", "pipeline"],
      nodes: [
        { id: "start", position: { x: 0, y: 0 }, data: { label: "Start", type: "source", status: "idle" }, type: "styledNode" },
        { id: "task1", position: { x: 0, y: 120 }, data: { label: "Task 1", type: "agent", status: "idle" }, type: "styledNode" },
        { id: "task2", position: { x: 0, y: 240 }, data: { label: "Task 2", type: "agent", status: "idle" }, type: "styledNode" },
        { id: "end", position: { x: 0, y: 360 }, data: { label: "End", type: "output", status: "idle" }, type: "styledNode" },
      ],
      edges: [
        { id: "e1", source: "start", target: "task1", animated: true, style: { stroke: "#3b82f6", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#3b82f6" } },
        { id: "e2", source: "task1", target: "task2", animated: true, style: { stroke: "#3b82f6", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#3b82f6" } },
        { id: "e3", source: "task2", target: "end", animated: true, style: { stroke: "#3b82f6", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#3b82f6" } },
      ],
    },
    {
      id: "parallel",
      name: "Parallel Fan-out",
      description: "Execute multiple agents simultaneously",
      color: "#22c55e",
      icon: <GitBranch className="w-4 h-4" />,
      tags: ["parallel", "fan-out"],
      nodes: [
        { id: "start", position: { x: 200, y: 0 }, data: { label: "Start", type: "source", status: "idle" }, type: "styledNode" },
        { id: "split", position: { x: 200, y: 100 }, data: { label: "Splitter", type: "splitter", status: "idle" }, type: "styledNode" },
        { id: "agent1", position: { x: 0, y: 200 }, data: { label: "Agent 1", type: "agent", status: "idle" }, type: "styledNode" },
        { id: "agent2", position: { x: 200, y: 200 }, data: { label: "Agent 2", type: "agent", status: "idle" }, type: "styledNode" },
        { id: "agent3", position: { x: 400, y: 200 }, data: { label: "Agent 3", type: "agent", status: "idle" }, type: "styledNode" },
        { id: "agg", position: { x: 200, y: 300 }, data: { label: "Aggregator", type: "aggregator", status: "idle" }, type: "styledNode" },
        { id: "end", position: { x: 200, y: 400 }, data: { label: "End", type: "output", status: "idle" }, type: "styledNode" },
      ],
      edges: [
        { id: "e1", source: "start", target: "split", animated: true, style: { stroke: "#3b82f6", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#3b82f6" } },
        { id: "e2", source: "split", target: "agent1", animated: true, style: { stroke: "#22c55e", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#22c55e" } },
        { id: "e3", source: "split", target: "agent2", animated: true, style: { stroke: "#22c55e", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#22c55e" } },
        { id: "e4", source: "split", target: "agent3", animated: true, style: { stroke: "#22c55e", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#22c55e" } },
        { id: "e5", source: "agent1", target: "agg", animated: true, style: { stroke: "#14b8a6", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#14b8a6" } },
        { id: "e6", source: "agent2", target: "agg", animated: true, style: { stroke: "#14b8a6", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#14b8a6" } },
        { id: "e7", source: "agent3", target: "agg", animated: true, style: { stroke: "#14b8a6", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#14b8a6" } },
        { id: "e8", source: "agg", target: "end", animated: true, style: { stroke: "#06b6d4", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#06b6d4" } },
      ],
    },
    {
      id: "conditional",
      name: "Conditional Router",
      description: "Branch based on output conditions",
      color: "#ec4899",
      icon: <GitBranch className="w-4 h-4" />,
      tags: ["branching", "conditional"],
      nodes: [
        { id: "start", position: { x: 200, y: 0 }, data: { label: "Start", type: "source", status: "idle" }, type: "styledNode" },
        { id: "router", position: { x: 200, y: 100 }, data: { label: "Router", type: "router", status: "idle" }, type: "styledNode" },
        { id: "pathA", position: { x: 0, y: 200 }, data: { label: "Path A", type: "agent", status: "idle" }, type: "styledNode" },
        { id: "pathB", position: { x: 400, y: 200 }, data: { label: "Path B", type: "agent", status: "idle" }, type: "styledNode" },
        { id: "end", position: { x: 200, y: 300 }, data: { label: "End", type: "output", status: "idle" }, type: "styledNode" },
      ],
      edges: [
        { id: "e1", source: "start", target: "router", animated: true, style: { stroke: "#3b82f6", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#3b82f6" } },
        { id: "e2", source: "router", target: "pathA", animated: true, label: "if true", style: { stroke: "#22c55e", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#22c55e" } },
        { id: "e3", source: "router", target: "pathB", animated: true, label: "if false", style: { stroke: "#ef4444", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#ef4444" } },
        { id: "e4", source: "pathA", target: "end", animated: true, style: { stroke: "#06b6d4", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#06b6d4" } },
        { id: "e5", source: "pathB", target: "end", animated: true, style: { stroke: "#06b6d4", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#06b6d4" } },
      ],
    },
    {
      id: "llm_enhanced",
      name: "LLM Enhanced Flow",
      description: "Agent + LLM + Agent pattern",
      color: "#a855f7",
      icon: <Sparkles className="w-4 h-4" />,
      tags: ["llm", "enhanced"],
      nodes: [
        { id: "start", position: { x: 200, y: 0 }, data: { label: "Start", type: "source", status: "idle" }, type: "styledNode" },
        { id: "agent", position: { x: 200, y: 100 }, data: { label: "Agent", type: "agent", status: "idle" }, type: "styledNode" },
        { id: "llm", position: { x: 200, y: 200 }, data: { label: "LLM", type: "llm", status: "idle" }, type: "styledNode" },
        { id: "review", position: { x: 200, y: 300 }, data: { label: "Review", type: "agent", status: "idle" }, type: "styledNode" },
        { id: "end", position: { x: 200, y: 400 }, data: { label: "End", type: "output", status: "idle" }, type: "styledNode" },
      ],
      edges: [
        { id: "e1", source: "start", target: "agent", animated: true, style: { stroke: "#3b82f6", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#3b82f6" } },
        { id: "e2", source: "agent", target: "llm", animated: true, style: { stroke: "#a855f7", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#a855f7" } },
        { id: "e3", source: "llm", target: "review", animated: true, style: { stroke: "#3b82f6", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#3b82f6" } },
        { id: "e4", source: "review", target: "end", animated: true, style: { stroke: "#06b6d4", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#06b6d4" } },
      ],
    },
    {
      id: "research",
      name: "Research Pipeline",
      description: "Explore + Librarian + Synthesis",
      color: "#06b6d4",
      icon: <Search className="w-4 h-4" />,
      tags: ["research", "external"],
      nodes: [
        { id: "start", position: { x: 200, y: 0 }, data: { label: "Start", type: "source", status: "idle" }, type: "styledNode" },
        { id: "explore", position: { x: 0, y: 100 }, data: { label: "Explore", type: "agent", status: "idle" }, type: "styledNode" },
        { id: "librarian", position: { x: 400, y: 100 }, data: { label: "Librarian", type: "agent", status: "idle" }, type: "styledNode" },
        { id: "synth", position: { x: 200, y: 200 }, data: { label: "Synthesize", type: "llm", status: "idle" }, type: "styledNode" },
        { id: "end", position: { x: 200, y: 300 }, data: { label: "End", type: "output", status: "idle" }, type: "styledNode" },
      ],
      edges: [
        { id: "e1", source: "start", target: "explore", animated: true, style: { stroke: "#06b6d4", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#06b6d4" } },
        { id: "e2", source: "start", target: "librarian", animated: true, style: { stroke: "#84cc16", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#84cc16" } },
        { id: "e3", source: "explore", target: "synth", animated: true, style: { stroke: "#a855f7", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#a855f7" } },
        { id: "e4", source: "librarian", target: "synth", animated: true, style: { stroke: "#a855f7", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#a855f7" } },
        { id: "e5", source: "synth", target: "end", animated: true, style: { stroke: "#06b6d4", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#06b6d4" } },
      ],
    },
    {
      id: "review",
      name: "Review Chain",
      description: "Implement → Review → Iterate",
      color: "#ef4444",
      icon: <Eye className="w-4 h-4" />,
      tags: ["review", "quality"],
      nodes: [
        { id: "start", position: { x: 200, y: 0 }, data: { label: "Start", type: "source", status: "idle" }, type: "styledNode" },
        { id: "implement", position: { x: 200, y: 100 }, data: { label: "Implement", type: "agent", status: "idle" }, type: "styledNode" },
        { id: "oracle", position: { x: 200, y: 200 }, data: { label: "Oracle", type: "agent", status: "idle" }, type: "styledNode" },
        { id: "momus", position: { x: 200, y: 300 }, data: { label: "Momus", type: "agent", status: "idle" }, type: "styledNode" },
        { id: "end", position: { x: 200, y: 400 }, data: { label: "End", type: "output", status: "idle" }, type: "styledNode" },
      ],
      edges: [
        { id: "e1", source: "start", target: "implement", animated: true, style: { stroke: "#3b82f6", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#3b82f6" } },
        { id: "e2", source: "implement", target: "oracle", animated: true, style: { stroke: "#3b82f6", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#3b82f6" } },
        { id: "e3", source: "oracle", target: "momus", animated: true, style: { stroke: "#ef4444", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#ef4444" } },
        { id: "e4", source: "momus", target: "end", animated: true, style: { stroke: "#06b6d4", strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#06b6d4" } },
      ],
    },
  ];
  
  const [customTemplates, setCustomTemplates] = useState<WorkflowTemplate[]>([]);
  
  const exportTemplates = () => {
    const data = {
      customTemplates,
      exportedAt: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const date = new Date().toISOString().split("T")[0];
    a.href = url;
    a.download = `nxyme-templates-${date}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };
  
  const importTemplates = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target?.result as string);
        if (data.customTemplates && Array.isArray(data.customTemplates)) {
          setCustomTemplates([...customTemplates, ...data.customTemplates]);
        }
      } catch (err) {
        console.error("Failed to import templates:", err);
      }
    };
    reader.readAsText(file);
    event.target.value = "";
  };
  
  // Transform session state and tools into log entries
  const logs = session ? [
    { id: "1", timestamp: new Date().toISOString().replace("T", " ").split(".")[0], level: "info", message: `Session active: ${session.current_task || 'idle'}` },
    ...(session.active_tasks?.map((taskId, idx) => ({
      id: String(idx + 2),
      timestamp: new Date().toISOString().replace("T", " ").split(".")[0],
      level: "info" as const,
      message: `Active task: ${taskId}`,
    })) || []),
    ...(tools.length > 0 ? [{ id: String(tools.length + 2), timestamp: new Date().toISOString().replace("T", " ").split(".")[0], level: "info" as const, message: `Available tools: ${tools.map(t => t.name).join(', ')}` }] : []),
  ] : [{ id: "1", timestamp: new Date().toISOString().replace("T", " ").split(".")[0], level: "info", message: "Connecting to orchestration API..." }];

  // dnd-kit sensorsfor drag-drop
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Generate dependency edges when tasks have dependencies
  useEffect(() => {
    // Get existing edges that are not dependency edges (keep the original flow edges)
    const flowEdges = edges.filter(e => !e.id.startsWith('dep-'));
    
    // Create dependency edges from tasks
    const dependencyEdges: Edge[] = [];
    tasks.forEach(task => {
      if (task.dependsOn && task.dependsOn.length > 0) {
        task.dependsOn.forEach(depId => {
          // Only add edge if both nodes exist in the graph
          const depTask = tasks.find(t => t.id === depId);
          if (depTask) {
            // Create a visual edge between task nodes using special dependency edge
            dependencyEdges.push({
              id: `dep-${depId}-${task.id}`,
              source: depId,
              target: task.id,
              type: 'smoothstep',
              animated: false,
              label: 'depends on',
              style: { stroke: "#8b5cf6", strokeWidth: 2, strokeDasharray: "5,5" },
              markerEnd: { type: MarkerType.ArrowClosed, color: "#8b5cf6" },
              labelStyle: { fill: "#8b5cf6", fontWeight: 500 },
              labelBgStyle: { fill: "#1e293b", fillOpacity: 0.9 },
            });
          }
        });
      }
    });
    
    // Combine flow edges with dependency edges
    setEdges([...flowEdges, ...dependencyEdges]);
  }, [tasks, setEdges]);

  // Handle drag end for task reordering
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIndex = tasks.findIndex((t) => t.id === active.id);
      const newIndex = tasks.findIndex((t) => t.id === over.id);
      reorderTasks(oldIndex, newIndex);
    }
  };

  // Initialize nodes based on active agents
  useEffect(() => {
    setNodes(generateInitialNodes(activeAgents));
    setEdges(generateInitialEdges(activeAgents));
    // Save to history
    historyRef.current = [generateInitialNodes(activeAgents)];
    historyIndexRef.current = 0;
  }, [activeAgents, setNodes, setEdges]);

  // Real session state updates handled by useSessionState hook automatically
  // No need for simulated polling - useSessionState provides refetchInterval

  // Real workflow state from session - update nodes based on actual backend state
  useEffect(() => {
    if (!session || !isRunning || isPaused) return;

    // Update node statuses based on actual session state
    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === "user" || node.id === "result") return node;

        // Use session state to determine actual node status
        const activeTasks = session.active_tasks || [];
        const isActive = activeTasks.includes(node.id);
        
        return {
          ...node,
          data: { 
            ...node.data, 
            status: isActive ? "running" : (node.data.status === "completed" ? "completed" : "idle"),
          },
        };
      })
    );

    // Update progress based on actual session
    setProgress((prev) => {
      const total = nodes.filter((n) => n.id !== "user" && n.id !== "result").length;
      const active = session.active_tasks?.length || 0;
      return { current: active, total };
    });
  }, [session, isRunning, isPaused, nodes, setNodes]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "f" && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const target = e.target as HTMLElement;
        if (target.tagName !== "INPUT" && target.tagName !== "TEXTAREA" && target.tagName !== "SELECT") {
          e.preventDefault();
          setFocusMode((prev) => !prev);
        }
      }
      // Ctrl+S: Save
      if (e.ctrlKey && e.key === "s") {
        e.preventDefault();
        const workflow = { nodes, edges, activeAgents };
        localStorage.setItem("orchestration-workflow", JSON.stringify(workflow));
      }
      // Ctrl+Z: Undo
      if (e.ctrlKey && e.key === "z" && !e.shiftKey) {
        e.preventDefault();
        if (historyIndexRef.current > 0) {
          historyIndexRef.current -= 1;
          setNodes(historyRef.current[historyIndexRef.current]);
        }
      }
      // Ctrl+Y or Ctrl+Shift+Z: Redo
      if ((e.ctrlKey && e.key === "y") || (e.ctrlKey && e.shiftKey && e.key === "z")) {
        e.preventDefault();
        if (historyIndexRef.current < historyRef.current.length - 1) {
          historyIndexRef.current += 1;
          setNodes(historyRef.current[historyIndexRef.current]);
        }
      }
      // Delete: Remove selected nodes
      if (e.key === "Delete" && selectedNodes.length > 0) {
        setNodes((nds) => nds.filter((n) => !selectedNodes.includes(n.id)));
        setSelectedNodes([]);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [nodes, edges, activeAgents, selectedNodes, setNodes]);

  // Toggle edge labels visibility
  useEffect(() => {
    setEdges((eds) => 
      eds.map((edge) => ({
        ...edge,
        label: showEdgeLabels ? (edge.label || '') : undefined,
      }))
    );
  }, [showEdgeLabels, setEdges]);

  // Handle node selection
  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    if (event.ctrlKey || event.metaKey) {
      // Multi-select with Ctrl+click
      setSelectedNodes((prev) => 
        prev.includes(node.id) 
          ? prev.filter((id) => id !== node.id)
          : [...prev, node.id]
      );
      // Clear selected node panel on multi-select
      if (selectedNode?.id === node.id) {
        setSelectedNode(null);
      }
    } else {
      // Single select - also show in details panel
      setSelectedNodes([node.id]);
      setSelectedNode(node);
    }
  }, [selectedNode]);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge({ ...params, animated: true }, eds)),
    [setEdges]
  );

  const handleAddTask = () => {
    if (!newTask.trim()) return;
    const task: Task = {
      id: `task-${Date.now()}`,
      description: newTask,
      status: "pending",
      priority: newTaskPriority,
      createdAt: new Date(),
    };
    useTaskStore.getState().addTask(task);
    setNewTask("");
  };

  const toggleAgent = (agentId: string) => {
    setAgentConfigs(prev => 
      prev.map(a => a.id === agentId ? { ...a, enabled: !a.enabled } : a)
    );
  };

  const updateTimeout = (agentId: string, timeout: number) => {
    setAgentConfigs(prev => 
      prev.map(a => a.id === agentId ? { ...a, timeout } : a)
    );
  };

  const updateMaxRetries = (agentId: string, maxRetries: number) => {
    setAgentConfigs(prev => 
      prev.map(a => a.id === agentId ? { ...a, maxRetries } : a)
    );
  };

  const updateCapacity = (agentId: string, capacity: number) => {
    setAgentConfigs(prev => 
      prev.map(a => a.id === agentId ? { ...a, capacity } : a)
    );
  };

  const updateModel = (agentId: string, model: string) => {
    setAgentConfigs(prev => 
      prev.map(a => a.id === agentId ? { ...a, model } : a)
    );
  };

  const updateColor = (agentId: string, color: string) => {
    setAgentConfigs(prev => 
      prev.map(a => a.id === agentId ? { ...a, color } : a)
    );
  };

  // Export queue to JSON
  const exportQueue = () => {
    const data = {
      tasks: tasks,
      agentsConfig: activeAgents,
      exportedAt: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const date = new Date().toISOString().split("T")[0];
    a.href = url;
    a.download = `nxyme-queue-${date}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Import queue from JSON
  const importQueue = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target?.result as string);
        if (data.tasks && Array.isArray(data.tasks)) {
          setTasks(data.tasks);
        }
      } catch (err) {
        console.error("Failed to import queue:", err);
      }
    };
    reader.readAsText(file);
    event.target.value = "";
  };

  const applyChanges = () => {
    setActiveAgents(agentConfigs);
  };

  const resetConfiguration = () => {
    setAgentConfigs(DEFAULT_AGENTS);
  };

  // Calculate metrics
  const completedTasks = tasks.filter((t) => t.status === "completed").length;
  const runningTasks = tasks.filter((t) => t.status === "running").length;
  const pendingTasks = tasks.filter((t) => t.status === "pending").length;
  const enabledCount = activeAgents.filter(a => a.enabled).length;

  return (
    <div className={`container mx-auto py-8 ${focusMode ? "border-2 border-dashed border-blue-500/30 bg-blue-500/5" : ""}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">Orchestration</h1>
          <div className="flex items-center gap-4 mt-1">
            <p className="text-muted-foreground">Modular agent orchestration visualization</p>
            {backendAvailable && (
              <div className="flex items-center gap-2 text-xs">
                <span className="px-2 py-0.5 rounded-full bg-green-500/20 text-green-400 border border-green-500/30">
                  Live
                </span>
                <span className="text-slate-500">
                  {effectiveAgents.length} agents
                </span>
              </div>
            )}
            {!backendAvailable && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">
                Fallback Mode
              </span>
            )}
            {backendAvailable && catalystState && (
              <div className="flex items-center gap-2 text-xs">
                <span className={`px-2 py-0.5 rounded-full border ${
                  catalystState === "FLOW" ? "bg-green-500/20 text-green-400 border-green-500/30" :
                  catalystState === "FRICTION" ? "bg-red-500/20 text-red-400 border-red-500/30" :
                  catalystState === "ADAPT" ? "bg-blue-500/20 text-blue-400 border-blue-500/30" :
                  "bg-slate-500/20 text-slate-400 border-slate-500/30"
                }`}>
                  {catalystState}
                </span>
                {catalystConfidence > 0 && (
                  <span className="text-slate-500">{Math.round(catalystConfidence * 100)}%</span>
                )}
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Step-by-step mode toggle */}
          <div className="flex items-center gap-2 mr-2">
            <label className="text-xs text-slate-400 flex items-center gap-1">
              <SkipForward className="w-3 h-3" />
              Step Mode
            </label>
            <Switch
              checked={stepMode}
              onCheckedChange={setStepMode}
              className="scale-75"
            />
          </div>
          {/* Focus Mode toggle */}
          <div className="flex items-center gap-2 mr-2">
            <label className="text-xs text-slate-400 flex items-center gap-1">
              <Eye className="w-3 h-3" />
              Focus Mode
            </label>
            <Switch
              checked={focusMode}
              onCheckedChange={setFocusMode}
              className="scale-75"
            />
            <kbd className="text-[10px] text-slate-500 bg-slate-800 px-1 py-0.5 rounded border border-slate-700">F</kbd>
          </div>
          <div className="flex items-center gap-2 mr-2">
            <label className="text-xs text-slate-400 flex items-center gap-1">
              <Layers className="w-3 h-3" />
              Compact
            </label>
            <Switch
              checked={compactMode}
              onCheckedChange={setCompactMode}
              className="scale-75"
            />
          </div>
          {/* Execution Controls */}
          {isRunning ? (
            <div className="flex items-center gap-2 mr-2">
              <Button
                variant={isPaused ? "default" : "outline"}
                size="sm"
                onClick={() => setIsPaused(!isPaused)}
                className={isPaused ? "bg-yellow-600 hover:bg-yellow-700" : ""}
              >
                {isPaused ? (
                  <>
                    <Play className="w-4 h-4 mr-1" />
                    Resume
                  </>
                ) : (
                  <>
                    <Pause className="w-4 h-4 mr-1" />
                    Pause
                  </>
                )}
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => {
                  setIsRunning(false);
                  setIsPaused(false);
                }}
              >
                <Square className="w-4 h-4 mr-1" />
                Stop
              </Button>
              {/* Progress bar */}
              <div className="flex items-center gap-2 ml-2">
                <div className="w-32 h-2 bg-slate-700 rounded-full overflow-hidden">
                  <div 
                    className={`h-full transition-all duration-300 ${isRunning && !isPaused ? "bg-gradient-to-r from-green-400 via-blue-400 to-green-400 bg-[length:200%_100%] animate-pulse" : "bg-green-500"}`}
                    style={{ width: progress.total > 0 ? `${(progress.current / progress.total) * 100}%` : '0%' }}
                  />
                </div>
                <span className="text-xs text-slate-400">
                  {progress.total > 0 ? Math.round((progress.current / progress.total) * 100) : 0}%
                </span>
                {isRunning && !isPaused && executionStartTime && (
                  <span className="text-xs text-blue-400">
                    ~{Math.max(1, Math.round((progress.total - progress.current) * 2.5))}s remaining
                  </span>
                )}
              </div>
            </div>
          ) : (
            <Button
              variant="default"
              size="sm"
              onClick={() => {
                setIsRunning(true);
                setExecutionStartTime(Date.now());
              }}
              className="bg-green-600 hover:bg-green-700"
            >
              <Play className="w-4 h-4 mr-1" />
              Start
            </Button>
          )}
          <Button 
            variant={isConfigMode ? "default" : "outline"}
            size="sm"
            onClick={() => setIsConfigMode(!isConfigMode)}
          >
            <Settings className="w-4 h-4 mr-2" />
            {isConfigMode ? "Done" : "Configure"}
          </Button>
          <Button variant="outline" size="sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          {/* Export/Import Queue buttons */}
          <Button variant="outline" size="sm" onClick={exportQueue}>
            <FileDown className="w-4 h-4 mr-2" />
            Export Queue
          </Button>
          <div className="relative">
            <input
              type="file"
              accept=".json"
              onChange={importQueue}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
            <Button variant="outline" size="sm" asChild>
              <span>
                <FileUp className="w-4 h-4 mr-2" />
                Import Queue
              </span>
            </Button>
          </div>
          {/* Save/Load buttons */}
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => {
              const workflow = { 
                nodes, 
                edges, 
                activeAgents,
                execution_mode: "dag",
                config: { fail_fast: true, max_parallel_tasks: 5 },
                saved_at: new Date().toISOString()
              };
              localStorage.setItem("orchestration-workflow", JSON.stringify(workflow));
            }}
          >
            <Save className="w-4 h-4 mr-2" />
            Save
          </Button>
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => {
              const saved = localStorage.getItem("orchestration-workflow");
              if (saved) {
                try {
                  const workflow = JSON.parse(saved);
                  setNodes(workflow.nodes || []);
                  setEdges(workflow.edges || []);
                  setActiveAgents(workflow.activeAgents || DEFAULT_AGENTS);
                } catch (e) {
                  console.error("Failed to load workflow:", e);
                }
              }
            }}
          >
            <Upload className="w-4 h-4 mr-2" />
            Load
          </Button>
          {/* WebSocket Connection Status */}
          <div className="flex items-center gap-2 ml-2 px-3 py-1 rounded-full bg-slate-800 border border-slate-700">
            {wsConnected ? (
              <>
                <Wifi className="w-4 h-4 text-green-400" />
                <span className="text-xs text-green-400">Connected</span>
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4 text-red-400" />
                <span className="text-xs text-red-400">Offline</span>
              </>
            )}
          </div>
          {/* Clear Completed Button */}
          {completedTasks > 0 && (
            <Button 
              variant="outline" 
              size="sm"
              className="text-yellow-400 border-yellow-500/50 hover:bg-yellow-500/10"
              onClick={() => setClearingCompleted(true)}
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Clear Completed ({completedTasks})
            </Button>
          )}
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-400">Completed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-400">{completedTasks}</div>
          </CardContent>
        </Card>
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-400">Running</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-400">{runningTasks}</div>
          </CardContent>
        </Card>
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-400">Pending</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-slate-400">{pendingTasks}</div>
          </CardContent>
        </Card>
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-400">Active Agents</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{enabledCount}</div>
          </CardContent>
        </Card>
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-400">Total Configured</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{activeAgents.length}</div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="tasks" className="w-full">
        <TabsList className="mb-4">
          <TabsTrigger value="tasks">Tasks</TabsTrigger>
          <TabsTrigger value="nodes">Node Palette</TabsTrigger>
          <TabsTrigger value="execution">Execution</TabsTrigger>
          <TabsTrigger value="agents">Agents</TabsTrigger>
          <TabsTrigger value="policy">Policy</TabsTrigger>
          <TabsTrigger value="templates">Templates</TabsTrigger>
        </TabsList>

        <TabsContent value="nodes">
          <Card>
            <CardHeader>
              <CardTitle>Add Nodes to Workflow</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { type: "agent", label: "Agent", color: "#22c55e", description: "Execute task with agent" },
                  { type: "router", label: "Router", color: "#ec4899", description: "Conditional branching" },
                  { type: "splitter", label: "Splitter", color: "#f97316", description: "Fan-out to parallel" },
                  { type: "aggregator", label: "Aggregator", color: "#14b8a6", description: "Fan-in collection" },
                  { type: "llm", label: "LLM Task", color: "#a855f7", description: "Direct LLM call" },
                  { type: "tool", label: "Tool", color: "#0ea5e9", description: "Execute tool" },
                  { type: "subflow", label: "Subflow", color: "#6366f1", description: "Nested workflow" },
                ].map((nodeType) => (
                  <div
                    key={nodeType.type}
                    className="p-4 rounded-lg border-2 cursor-pointer transition-all hover:scale-105"
                    style={{ borderColor: nodeType.color + "40", background: nodeType.color + "10" }}
                    onClick={() => {
                      const newNode: Node = {
                        id: `node_${Date.now()}_${Math.random().toString(36).slice(2, 5)}`,
                        type: "styledNode",
                        position: { x: 100 + Math.random() * 200, y: 100 + Math.random() * 200 },
                        data: { 
                          label: nodeType.label, 
                          type: nodeType.type,
                          subtitle: nodeType.description,
                          status: "idle" 
                        },
                      };
                      setNodes((nds) => [...nds, newNode]);
                    }}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <span style={{ color: nodeType.color }}>{nodeIcons[nodeType.type as keyof typeof nodeIcons]}</span>
                      <span className="font-medium text-sm">{nodeType.label}</span>
                    </div>
                    <p className="text-xs text-slate-400">{nodeType.description}</p>
                  </div>
                ))}
              </div>
              <div className="mt-6 p-4 bg-slate-800/50 rounded-lg">
                <h4 className="text-sm font-medium mb-2">Current Nodes ({nodes.length})</h4>
                <div className="flex flex-wrap gap-2">
                  {nodes.map((node) => (
                    <Badge 
                      key={node.id}
                      variant="outline"
                      className={`cursor-pointer ${compactMode ? 'group relative' : ''}`}
                      style={{ borderColor: nodeStyles[node.data.type as keyof typeof nodeStyles]?.border?.split(" ")[2] || "#22c55e" }}
                      onClick={() => {
                        setSelectedNodes([node.id]);
                      }}
                      title={compactMode && node.data.subtitle ? String(node.data.subtitle) : undefined}
                    >
                      <span className="mr-1">{(nodeIcons as Record<string, React.ReactNode>)[String(node.data.type)] || nodeIcons.agent}</span>
                      <span>{String(node.data.label)}</span>
                    </Badge>
                  ))}
                  {nodes.length === 0 && <span className="text-sm text-slate-400">Click a node type above to add</span>}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="tasks">
          <Card>
            <CardContent className="p-4">
              {/* Add Task Input */}
              <div className="flex gap-2 mb-4">
                <Input
                  placeholder="Add new task..."
                  value={newTask}
                  onChange={(e) => setNewTask(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") handleAddTask(); }}
                  className="flex-1"
                />
                <select
                  value={newTaskPriority}
                  onChange={(e) => setNewTaskPriority(e.target.value as "low" | "medium" | "high" | "urgent")}
                  className="bg-slate-800 border border-slate-600 rounded px-2 py-2 text-sm text-slate-200"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="urgent">Urgent</option>
                </select>
                <Button onClick={handleAddTask}>
                  <Plus className="w-4 h-4 mr-2" />
                  Add Task
                </Button>
              </div>
              
              {/* Drag-Drop Task Queue */}
              <div className="border border-slate-700 rounded-lg overflow-hidden bg-slate-900/50">
                {tasks.length === 0 ? (
                  <div className="h-[400px] flex items-center justify-center text-slate-400">
                    <div className="text-center">
                      <Target className="w-12 h-12 mx-auto mb-2 opacity-50" />
                      <p>No tasks yet. Add a task above to get started.</p>
                    </div>
                  </div>
                ) : (
                  <DndContext
                    sensors={sensors}
                    collisionDetection={closestCenter}
                    onDragEnd={handleDragEnd}
                  >
                    <SortableContext
                      items={tasks.map(t => t.id)}
                      strategy={verticalListSortingStrategy}
                    >
                      <div className="h-[400px] overflow-y-auto p-3 space-y-2">
                        {tasks.map((task) => (
                          <SortableTaskItem
                            key={task.id}
                            task={task}
                            onEdit={setEditingTask}
                            onDelete={setDeletingTask}
                            onAddDependency={addDependency}
                            onRemoveDependency={(taskId, depId) => useTaskStore.getState().removeDependency(taskId, depId)}
                            allTasks={tasks}
                            isLinking={isLinking}
                            linkingTaskId={linkingTaskId}
                            onStartLink={(taskId) => {
                              setIsLinking(true);
                              setLinkingTaskId(taskId);
                            }}
                            onCancelLink={() => {
                              setIsLinking(false);
                              setLinkingTaskId(null);
                            }}
                            compactMode={compactMode}
                            expandedTaskId={expandedTaskId}
                            onToggleExpand={(taskId) => setExpandedTaskId(expandedTaskId === taskId ? null : taskId)}
                          />
                        ))}
                      </div>
                    </SortableContext>
                  </DndContext>
                )}
              </div>
              
              {/* ReactFlow Visualization */}
              <div className="mt-4 border border-slate-700 rounded-lg overflow-hidden bg-slate-900/50">
                <ReactFlow
                  nodes={nodes.map((node) => ({
                    ...node,
                    selected: selectedNodes.includes(node.id),
                  }))}
                  edges={edges}
                  onNodesChange={onNodesChange}
                  onEdgesChange={onEdgesChange}
                  onConnect={onConnect}
                  onNodeClick={onNodeClick}
                  nodeTypes={nodeTypes}
                  fitView
                  attributionPosition="bottom-left"
                  proOptions={{ hideAttribution: true }}
                >
                  <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#334155" />
                  <Controls className="bg-slate-800 border-slate-700 text-slate-200" />
                  {showMinimap && (
                    <MiniMap 
                      nodeColor={(node) => {
                        const data = node.data as { type?: string };
                        switch (data?.type) {
                          case "source": return "#3b82f6";
                          case "orchestrator": return "#f59e0b";
                          case "output": return "#06b6d4";
                          default: return "#22c55e";
                        }
                      }}
                      maskColor="rgba(15, 23, 42, 0.8)"
                      className="bg-slate-800 border-slate-700"
                    />
                  )}
                  {/* Visualization Controls Panel */}
                  <Panel position="top-right" className="bg-slate-800/90 border border-slate-700 p-3 rounded-lg">
                    <div className="text-xs space-y-2">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-slate-400 font-medium">View</span>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        <Button 
                          variant="outline" 
                          size="sm" 
                          className="h-6 px-2 text-xs"
                          onClick={() => fitView({ padding: 0.2 })}
                          title="Zoom to Fit"
                        >
                          <ZoomIn className="w-3 h-3 mr-1" />
                          Fit
                        </Button>
                        <Button 
                          variant={showEdgeLabels ? "default" : "outline"} 
                          size="sm" 
                          className="h-6 px-2 text-xs"
                          onClick={() => setShowEdgeLabels(!showEdgeLabels)}
                          title="Toggle Edge Labels"
                        >
                          <MapPin className="w-3 h-3 mr-1" />
                          Labels
                        </Button>
                        <Button 
                          variant={showMinimap ? "default" : "outline"} 
                          size="sm" 
                          className="h-6 px-2 text-xs"
                          onClick={() => setShowMinimap(!showMinimap)}
                          title="Toggle Minimap"
                        >
                          <Map className="w-3 h-3 mr-1" />
                          Map
                        </Button>
                        <Button 
                          variant="outline" 
                          size="sm" 
                          className="h-6 px-2 text-xs"
                          onClick={() => fitView({ padding: 0.5 })}
                          title="Center Graph"
                        >
                          <Maximize2 className="w-3 h-3 mr-1" />
                          Center
                        </Button>
                        <Button 
                          variant={showLogs ? "default" : "outline"} 
                          size="sm" 
                          className="h-6 px-2 text-xs"
                          onClick={() => setShowLogs(!showLogs)}
                          title="Toggle Logs"
                        >
                          <FileText className="w-3 h-3 mr-1" />
                          Logs
                        </Button>
                        <Button 
                          variant="outline" 
                          size="sm" 
                          className="h-6 px-2 text-xs"
                          onClick={() => {
                            // Simple auto-arrange: organize nodes in a grid pattern
                            const centerX = 400;
                            const startY = 80;
                            const spacingX = 200;
                            const spacingY = 150;
                            
                            // Group nodes by type
                            const sourceNodes = nodes.filter(n => (n.data as {type?: string}).type === 'source');
                            const orchestratorNodes = nodes.filter(n => (n.data as {type?: string}).type === 'orchestrator');
                            const agentNodes = nodes.filter(n => (n.data as {type?: string}).type === 'agent');
                            const outputNodes = nodes.filter(n => (n.data as {type?: string}).type === 'output');
                            
                            const newNodes = nodes.map(node => {
                              const nodeType = (node.data as {type?: string}).type;
                              let newX = node.position.x;
                              let newY = node.position.y;
                              
                              if (nodeType === 'source') {
                                newX = centerX - 70;
                                newY = startY;
                              } else if (nodeType === 'orchestrator') {
                                newX = centerX - 70;
                                newY = startY + spacingY;
                              } else if (nodeType === 'agent') {
                                const idx = agentNodes.findIndex(n => n.id === node.id);
                                newX = centerX + (idx - Math.floor(agentNodes.length / 2)) * spacingX - 70;
                                newY = startY + spacingY * 2;
                              } else if (nodeType === 'output') {
                                newX = centerX - 70;
                                newY = startY + spacingY * 3;
                              }
                              
                              return { ...node, position: { x: newX, y: newY } };
                            });
                            
                            setNodes(newNodes);
                            // Save to history
                            historyRef.current = [...historyRef.current.slice(0, historyIndexRef.current + 1), newNodes];
                            historyIndexRef.current = historyRef.current.length - 1;
                          }}
                          title="Auto-Arrange Nodes"
                        >
                          <Map className="w-3 h-3 mr-1" />
                          Arrange
                        </Button>
                      </div>
                      <div className="border-t border-slate-600 pt-2 mt-2">
                        <div className="flex items-center gap-2">
                          <div className="w-2.5 h-2.5 rounded-full bg-yellow-400 animate-pulse" />
                          <span className="text-slate-300">Working</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-2.5 h-2.5 rounded-full bg-green-400" />
                          <span className="text-slate-300">Completed</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-2.5 h-2.5 rounded-full bg-slate-500" />
                          <span className="text-slate-300">Idle</span>
                        </div>
                      </div>
                    </div>
                  </Panel>
                </ReactFlow>
              </div>
              {/* Logs Panel - Collapsible at bottom */}
              {showLogs && (
                <div className="mt-2 border border-slate-700 rounded-lg bg-slate-900/80 overflow-hidden">
                  <div className="flex items-center justify-between px-3 py-2 bg-slate-800/50 border-b border-slate-700">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-slate-400" />
                      <span className="text-sm font-medium text-slate-300">Execution Logs</span>
                    </div>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="h-6 px-2"
                      onClick={() => setShowLogs(false)}
                    >
                      <ChevronDown className="w-4 h-4" />
                    </Button>
                  </div>
                  <div className="h-40 overflow-y-auto p-3 space-y-1">
                    {logs.map((log) => (
                      <div 
                        key={log.id} 
                        className={`text-xs flex items-start gap-2 ${
                          log.level === 'error' ? 'text-red-400' :
                          log.level === 'warn' ? 'text-yellow-400' :
                          'text-blue-400'
                        }`}
                      >
                        <span className="text-slate-500 shrink-0">{log.timestamp}</span>
                        <span className={`shrink-0 uppercase text-[10px] font-bold ${
                          log.level === 'error' ? 'text-red-500' :
                          log.level === 'warn' ? 'text-yellow-500' :
                          'text-blue-500'
                        }`}>[{log.level}]</span>
                        <span className="text-slate-300">{log.message}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="execution">
          <Card>
            <CardHeader>
              <CardTitle>Workflow Execution</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="p-4 bg-slate-800/50 rounded-lg">
                  <div className="text-sm text-slate-400 mb-1">Status</div>
                  <div className="flex items-center gap-2">
                    {isRunning ? (
                      <>
                        <div className={`w-3 h-3 rounded-full ${isPaused ? "bg-yellow-400" : "bg-green-400 animate-pulse"} ${isRunning && !isPaused ? "shadow-[0_0_8px_rgba(34,197,94,0.6)]" : ""}`} />
                        <span className="font-medium">{isPaused ? "Paused" : "Running"}</span>
                      </>
                    ) : (
                      <>
                        <div className="w-3 h-3 rounded-full bg-slate-500" />
                        <span className="font-medium">Idle</span>
                      </>
                    )}
                  </div>
                </div>
                <div className="p-4 bg-slate-800/50 rounded-lg">
                  <div className="text-sm text-slate-400 mb-1">Progress</div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
                      <div 
                        className={`h-full transition-all ${isRunning && !isPaused ? "bg-gradient-to-r from-green-400 via-blue-400 to-purple-400 bg-[length:200%_100%] animate-pulse" : "bg-green-500"}`}
                        style={{ width: progress.total > 0 ? `${(progress.current / progress.total) * 100}%` : '0%' }}
                      />
                    </div>
                    <span className="text-sm">{progress.total > 0 ? Math.round((progress.current / progress.total) * 100) : 0}%</span>
                  </div>
                  {isRunning && progress.total > 0 && (
                    <div className="text-xs text-blue-400 mt-1">
                      Executing node {progress.current + 1} of {progress.total}
                    </div>
                  )}
                </div>
                <div className="p-4 bg-slate-800/50 rounded-lg">
                  <div className="text-sm text-slate-400 mb-1">Total Duration</div>
                  <div className="font-medium">
                    {progress.current > 0 ? `${Math.floor((progress.current * 2.5))}s` : "0s"}
                  </div>
                </div>
              </div>

              <div className="mb-4 p-4 bg-slate-800/30 rounded-lg border border-slate-700">
                <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                  <Zap className="w-4 h-4 text-yellow-400" />
                  Cost & Time Estimation
                </h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <div className="text-xs text-slate-400">Est. Duration</div>
                    <div className="text-lg font-bold text-blue-400">
                      {nodes.filter(n => n.id !== 'user' && n.id !== 'result').length > 0 
                        ? `${nodes.filter(n => n.id !== 'user' && n.id !== 'result').length * 2.5}s`
                        : "0s"}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-400">Est. Cost</div>
                    <div className="text-lg font-bold text-green-400">
                      ${(nodes.filter(n => n.id !== 'user' && n.id !== 'result').length * 0.02).toFixed(2)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-400">Nodes</div>
                    <div className="text-lg font-bold">
                      {nodes.filter(n => n.id !== 'user' && n.id !== 'result').length}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-400">Parallel Paths</div>
                    <div className="text-lg font-bold text-purple-400">
                      {Math.max(...nodes.map(n => {
                        const outEdges = edges.filter(e => e.source === n.id).length;
                        return outEdges;
                      }), 0) || 1}
                    </div>
                  </div>
                </div>
              </div>

              <div className="mb-4">
                <h4 className="text-sm font-medium mb-2">Execution Timeline</h4>
                <div className="space-y-2 max-h-[300px] overflow-y-auto">
                  {nodes.filter(n => n.data.status && n.data.status !== "idle").length > 0 ? (
                    nodes.filter(n => n.data.status && n.data.status !== "idle").map((node, idx) => (
                      <div key={node.id} className="flex items-center gap-3 p-2 bg-slate-800/30 rounded">
                        <div className={`w-2 h-2 rounded-full ${
                          node.data.status === "completed" ? "bg-green-500" :
                          node.data.status === "failed" ? "bg-red-500" :
                          node.data.status === "running" ? "bg-yellow-400 animate-pulse" :
                          "bg-slate-500"
                        }`} />
                        <span className="text-sm flex-1">{String(node.data.label)}</span>
                        <Badge variant="outline" className="text-xs">
                          {String(node.data.status)}
                        </Badge>
                        <span className="text-xs text-slate-400">~{idx * 2.5}s</span>
                      </div>
                    ))
                  ) : (
                    <div className="text-sm text-slate-400 text-center py-4">
                      No execution history. Run the workflow to see timeline.
                    </div>
                  )}
                </div>
              </div>

              <div className="mb-4">
                <h4 className="text-sm font-medium mb-2">Node Status</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                  {nodes.map((node) => (
                    <div 
                      key={node.id}
                      className={`p-2 rounded border cursor-pointer transition-all hover:scale-105 ${
                        node.data.status === "completed" ? "border-green-500/50 bg-green-500/10" :
                        node.data.status === "failed" ? "border-red-500/50 bg-red-500/10" :
                        node.data.status === "running" ? "border-yellow-500/50 bg-yellow-500/10" :
                        "border-slate-700 bg-slate-800/30"
                      } ${selectedNodeDetails?.id === node.id ? 'ring-2 ring-blue-500' : ''}`}
                      onClick={() => setSelectedNodeDetails(selectedNodeDetails?.id === node.id ? null : node)}
                    >
                      <div className="flex items-center gap-2">
                        <span style={{ color: nodeStyles[node.data.type as keyof typeof nodeStyles]?.border?.split(" ")[2] || "#22c55e" }}>
                          {nodeIcons[node.data.type as keyof typeof nodeIcons]}
                        </span>
                        <span className="text-xs truncate">{String(node.data.label)}</span>
                      </div>
                      <div className={`text-xs mt-1 ${
                        node.data.status === "completed" ? "text-green-400" :
                        node.data.status === "failed" ? "text-red-400" :
                        node.data.status === "running" ? "text-yellow-400" :
                        "text-slate-400"
                      }`}>
                        {String(node.data.status || "idle")}
                      </div>
                    </div>
                  ))}
                  {nodes.length === 0 && (
                    <div className="col-span-4 text-sm text-slate-400 text-center py-4">
                      Add nodes from the Node Palette tab to build a workflow
                    </div>
                  )}
                </div>
                {selectedNodeDetails && (
                  <div className="mt-4 p-4 bg-slate-800/50 rounded-lg border border-slate-600">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span style={{ color: nodeStyles[selectedNodeDetails.data.type as keyof typeof nodeStyles]?.border?.split(" ")[2] || "#22c55e" }}>
                          {nodeIcons[selectedNodeDetails.data.type as keyof typeof nodeIcons]}
                        </span>
                        <span className="font-medium">{String(selectedNodeDetails.data.label)}</span>
                      </div>
                      <Button variant="ghost" size="sm" onClick={() => setSelectedNodeDetails(null)}>
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-slate-400">Type</span>
                        <span>{String(selectedNodeDetails.data.type || 'N/A')}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Status</span>
                        <span className={selectedNodeDetails.data.status === "completed" ? "text-green-400" : selectedNodeDetails.data.status === "failed" ? "text-red-400" : selectedNodeDetails.data.status === "running" ? "text-yellow-400" : "text-slate-300"}>
                          {String(selectedNodeDetails.data.status || "idle")}
                        </span>
                      </div>
                      {(selectedNodeDetails.data.subtitle as string) && (
                        <div className="flex justify-between">
                          <span className="text-slate-400">Description</span>
                          <span className="text-slate-300">{String(selectedNodeDetails.data.subtitle)}</span>
                        </div>
                      )}
                      <div className="border-t border-slate-700 pt-2 mt-2">
                        <div className="text-xs text-slate-500 mb-1">Input</div>
                        <div className="p-2 bg-slate-900 rounded text-xs font-mono text-slate-300">No input data</div>
                      </div>
                      <div>
                        <div className="text-xs text-slate-500 mb-1">Output</div>
                        <div className="p-2 bg-slate-900 rounded text-xs font-mono text-slate-300">No output data</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div>
                <h4 className="text-sm font-medium mb-2">Execution Logs</h4>
                <div className="bg-slate-900 rounded-lg p-4 max-h-[200px] overflow-y-auto font-mono text-xs">
                  {logs.slice(0, 10).map((log) => (
                    <div key={log.id} className="mb-1">
                      <span className="text-slate-500">[{log.timestamp}]</span>
                      <span className={`ml-2 ${
                        log.level === "error" ? "text-red-400" :
                        log.level === "warn" ? "text-yellow-400" :
                        "text-green-400"
                      }`}>
                        {log.level.toUpperCase()}
                      </span>
                      <span className="ml-2 text-slate-300">{log.message}</span>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="agents">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Agent Configuration</CardTitle>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={resetConfiguration}>
                    <RotateCcw className="w-4 h-4 mr-2" />
                    Reset Defaults
                  </Button>
                  <Button variant="default" size="sm" onClick={applyChanges}>
                    <Save className="w-4 h-4 mr-2" />
                    Apply Changes
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4">
                Configure individual agents. Click "Apply Changes" to save your configuration.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {agentConfigs.map((agent) => (
                  <div 
                    key={agent.id}
                    className={`flex flex-col p-4 rounded-lg border transition-all ${
                      agent.enabled 
                        ? "bg-slate-800/50 border-slate-600" 
                        : "bg-slate-900/30 border-slate-800 opacity-60"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div 
                          className="w-10 h-10 rounded-lg flex items-center justify-center"
                          style={{ backgroundColor: agent.color + "20" }}
                        >
                          <span style={{ color: agent.color }}>
                            {agent.icon}
                          </span>
                        </div>
                        <div>
                          <div className="font-medium">{agent.name}</div>
                          <div className="text-xs text-muted-foreground">{agent.role}</div>
                        </div>
                      </div>
                      <Switch
                        checked={agent.enabled}
                        onCheckedChange={() => toggleAgent(agent.id)}
                      />
                    </div>
                    <div className="space-y-3 text-sm">
                      <div className="flex items-center gap-2">
                        <label className="text-xs text-muted-foreground w-16">Timeout</label>
                        <input
                          type="number"
                          value={agent.timeout}
                          onChange={(e) => updateTimeout(agent.id, Number(e.target.value))}
                          disabled={!agent.enabled}
                          className="w-20 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs text-slate-200 disabled:opacity-50"
                          min={30}
                          max={600}
                        />
                        <span className="text-xs text-muted-foreground">sec</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <label className="text-xs text-muted-foreground w-16">Retries</label>
                        <input
                          type="number"
                          value={agent.maxRetries}
                          onChange={(e) => updateMaxRetries(agent.id, Number(e.target.value))}
                          disabled={!agent.enabled}
                          className="w-20 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs text-slate-200 disabled:opacity-50"
                          min={0}
                          max={10}
                        />
                      </div>
                      <div className="flex items-center gap-2">
                        <label className="text-xs text-muted-foreground w-16">Capacity</label>
                        <input
                          type="number"
                          value={agent.capacity}
                          onChange={(e) => updateCapacity(agent.id, Number(e.target.value))}
                          disabled={!agent.enabled}
                          className="w-20 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs text-slate-200 disabled:opacity-50"
                          min={1}
                          max={50}
                        />
                      </div>
                      <div className="flex items-center gap-2">
                        <label className="text-xs text-muted-foreground w-16">Model</label>
                        <select
                          value={agent.model}
                          onChange={(e) => updateModel(agent.id, e.target.value)}
                          disabled={!agent.enabled}
                          className="flex-1 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs text-slate-200 disabled:opacity-50"
                        >
                          <option value="GPT-4o">GPT-4o</option>
                          <option value="Claude 3.5 Sonnet">Claude 3.5 Sonnet</option>
                          <option value="Gemini 1.5 Pro">Gemini 1.5 Pro</option>
                        </select>
                      </div>
                      <div className="flex items-center gap-2">
                        <label className="text-xs text-muted-foreground w-16">Color</label>
                        <div className="flex gap-1">
                          {COLOR_OPTIONS.map((color) => (
                            <button
                              key={color}
                              onClick={() => updateColor(agent.id, color)}
                              className={`w-6 h-6 rounded-full transition-transform ${
                                agent.color === color ? "scale-110 ring-2 ring-white" : "hover:scale-105"
                              }`}
                              style={{ backgroundColor: color }}
                              disabled={!agent.enabled}
                            />
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="policy">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Global Policy Engine</CardTitle>
                <Button variant="default" size="sm" onClick={() => {
                  const newPolicy: GlobalPolicy = {
                    id: `policy_${Date.now()}`,
                    name: "New Policy",
                    enabled: true,
                    trigger: "always",
                    action: "allow",
                    priority: "medium",
                    conditions: [],
                  };
                  setGlobalPolicies([...globalPolicies, newPolicy]);
                }}>
                  <Plus className="w-4 h-4 mr-2" />
                  Add Policy
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4">
                Define global execution policies that apply to all workflows.
              </p>
              
              {globalPolicies.length === 0 ? (
                <div className="text-center py-8 text-slate-400">
                  <Shield className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p>No policies defined. Create one to get started.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {globalPolicies.map((policy) => (
                    <div 
                      key={policy.id}
                      className={`p-4 rounded-lg border transition-all ${
                        policy.enabled 
                          ? "bg-slate-800/50 border-slate-600" 
                          : "bg-slate-900/30 border-slate-800 opacity-60"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <Switch
                            checked={policy.enabled}
                            onCheckedChange={(checked) => {
                              setGlobalPolicies(globalPolicies.map(p => 
                                p.id === policy.id ? { ...p, enabled: checked } : p
                              ));
                            }}
                          />
                          <span className="font-medium">{policy.name}</span>
                          <Badge variant="outline" className={`text-xs ${
                            policy.priority === 'high' ? 'border-red-500 text-red-400' :
                            policy.priority === 'low' ? 'border-slate-500 text-slate-400' :
                            'border-yellow-500 text-yellow-400'
                          }`}>
                            {policy.priority}
                          </Badge>
                        </div>
                        <Button variant="ghost" size="sm" onClick={() => {
                          setGlobalPolicies(globalPolicies.filter(p => p.id !== policy.id));
                        }}>
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                        <div>
                          <div className="text-xs text-slate-400 mb-1">Trigger</div>
                          <select
                            value={policy.trigger}
                            onChange={(e) => {
                              setGlobalPolicies(globalPolicies.map(p => 
                                p.id === policy.id ? { ...p, trigger: e.target.value } : p
                              ));
                            }}
                            className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs"
                          >
                            <option value="always">Always</option>
                            <option value="on_error">On Error</option>
                            <option value="on_timeout">On Timeout</option>
                            <option value="on_high_cost">On High Cost</option>
                          </select>
                        </div>
                        <div>
                          <div className="text-xs text-slate-400 mb-1">Action</div>
                          <select
                            value={policy.action}
                            onChange={(e) => {
                              setGlobalPolicies(globalPolicies.map(p => 
                                p.id === policy.id ? { ...p, action: e.target.value } : p
                              ));
                            }}
                            className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs"
                          >
                            <option value="allow">Allow</option>
                            <option value="block">Block</option>
                            <option value="retry">Retry</option>
                            <option value="fallback">Fallback to Agent</option>
                          </select>
                        </div>
                        <div>
                          <div className="text-xs text-slate-400 mb-1">Priority</div>
                          <select
                            value={policy.priority}
                            onChange={(e) => {
                              setGlobalPolicies(globalPolicies.map(p => 
                                p.id === policy.id ? { ...p, priority: e.target.value as 'low' | 'medium' | 'high' } : p
                              ));
                            }}
                            className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs"
                          >
                            <option value="low">Low</option>
                            <option value="medium">Medium</option>
                            <option value="high">High</option>
                          </select>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              
              <div className="mt-6 p-4 bg-slate-800/30 rounded-lg border border-slate-700">
                <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                  <Zap className="w-4 h-4 text-yellow-400" />
                  Policy Summary
                </h4>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <div className="text-xs text-slate-400">Active Policies</div>
                    <div className="text-lg font-bold text-green-400">
                      {globalPolicies.filter(p => p.enabled).length}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-400">Block Rules</div>
                    <div className="text-lg font-bold text-red-400">
                      {globalPolicies.filter(p => p.enabled && p.action === 'block').length}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-400">Retry Rules</div>
                    <div className="text-lg font-bold text-yellow-400">
                      {globalPolicies.filter(p => p.enabled && p.action === 'retry').length}
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="templates">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Workflow Templates</CardTitle>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={exportTemplates}>
                    <FileDown className="w-4 h-4 mr-2" />
                    Export
                  </Button>
                  <div className="relative">
                    <input
                      type="file"
                      accept=".json"
                      onChange={importTemplates}
                      className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    />
                    <Button variant="outline" size="sm" asChild>
                      <span>
                        <FileUp className="w-4 h-4 mr-2" />
                        Import
                      </span>
                    </Button>
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4">
                Pre-built workflow patterns for common orchestration scenarios.
              </p>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {WORKFLOW_TEMPLATES.map((template) => (
                  <div 
                    key={template.id}
                    className="p-4 rounded-lg border border-slate-700 bg-slate-800/30 hover:bg-slate-800/50 hover:border-slate-600 transition-all cursor-pointer"
                    onClick={() => {
                      const templateNodes = template.nodes.map((n, idx) => ({
                        ...n,
                        position: { x: 100 + (idx % 2) * 200, y: 100 + Math.floor(idx / 2) * 150 },
                      }));
                      setNodes(templateNodes);
                      setEdges(template.edges || []);
                    }}
                  >
                    <div className="flex items-center gap-3 mb-3">
                      <div 
                        className="w-10 h-10 rounded-lg flex items-center justify-center"
                        style={{ backgroundColor: template.color + "20" }}
                      >
                        <span style={{ color: template.color }}>
                          {template.icon}
                        </span>
                      </div>
                      <div>
                        <div className="font-medium">{template.name}</div>
                        <div className="text-xs text-muted-foreground">{template.nodes.length} nodes</div>
                      </div>
                    </div>
                    <div className="text-xs text-slate-400 mb-3">{template.description}</div>
                    <div className="flex flex-wrap gap-1">
                      {template.tags.slice(0, 3).map((tag) => (
                        <Badge key={tag} variant="outline" className="text-[10px]">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
              
              <div className="mt-6">
                <h4 className="text-sm font-medium mb-3">Custom Templates</h4>
                {customTemplates.length === 0 ? (
                  <div className="text-center py-6 text-slate-400 border border-dashed border-slate-700 rounded-lg">
                    <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">Save current workflow as template</p>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="mt-2"
                      onClick={() => {
                        const newTemplate = {
                          id: `custom_${Date.now()}`,
                          name: `Workflow ${new Date().toLocaleDateString()}`,
                          description: "Custom workflow template",
                          color: "#3b82f6",
                          icon: <Workflow className="w-4 h-4" />,
                          tags: ["custom"],
                          nodes: nodes,
                          edges: edges,
                        };
                        setCustomTemplates([...customTemplates, newTemplate]);
                      }}
                    >
                      <Save className="w-4 h-4 mr-2" />
                      Save Current
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {customTemplates.map((template) => (
                      <div 
                        key={template.id}
                        className="flex items-center justify-between p-3 rounded-lg border border-slate-700 bg-slate-800/30"
                      >
                        <div className="flex items-center gap-3">
                          <Workflow className="w-4 h-4 text-blue-400" />
                          <span className="text-sm">{template.name}</span>
                          <Badge variant="outline" className="text-[10px]">
                            {template.nodes?.length || 0} nodes
                          </Badge>
                        </div>
                        <div className="flex gap-1">
                          <Button 
                            variant="ghost" 
                            size="sm"
                            onClick={() => {
                              if (template.nodes) setNodes(template.nodes);
                              if (template.edges) setEdges(template.edges);
                            }}
                          >
                            Load
                          </Button>
                          <Button 
                            variant="ghost" 
                            size="sm"
                            onClick={() => {
                              setCustomTemplates(customTemplates.filter(t => t.id !== template.id));
                            }}
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Edit Task Dialog */}
      <Dialog open={!!editingTask} onOpenChange={() => setEditingTask(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Task</DialogTitle>
            <DialogDescription>
              Modify the task description below.
            </DialogDescription>
          </DialogHeader>
          <Input
            value={editDescription}
            onChange={(e) => setEditDescription(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && editingTask) {
                updateTask(editingTask.id, { description: editDescription });
                setEditingTask(null);
              }
            }}
            className="mt-4"
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingTask(null)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                if (editingTask) {
                  updateTask(editingTask.id, { description: editDescription });
                  setEditingTask(null);
                }
              }}
            >
              <Check className="w-4 h-4 mr-2" />
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deletingTask} onOpenChange={() => setDeletingTask(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Task</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this task? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          {deletingTask && (
            <div className="mt-2">
              <div className="p-3 rounded-lg bg-slate-800/50 border border-slate-700 mb-3">
                <span className="text-sm">{deletingTask.description}</span>
              </div>
              {/* Show warning if task has dependents */}
              {getDependents(deletingTask.id).length > 0 && (
                <div className="p-3 rounded-lg bg-yellow-500/20 border border-yellow-500/50">
                  <div className="flex items-center gap-2 text-yellow-400 mb-2">
                    <AlertTriangle className="w-4 h-4" />
                    <span className="text-sm font-medium">Warning: This task has dependent tasks</span>
                  </div>
                  <div className="text-xs text-yellow-300">
                    The following tasks depend on this task and may break:
                  </div>
                  <ul className="mt-2 space-y-1">
                    {getDependents(deletingTask.id).map(dep => (
                      <li key={dep.id} className="text-xs text-yellow-300 flex items-center gap-1">
                        <Link2 className="w-3 h-3" />
                        {dep.description}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeletingTask(null)}>
              <X className="w-4 h-4 mr-2" />
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                if (deletingTask) {
                  removeTask(deletingTask.id);
                  setDeletingTask(null);
                }
              }}
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Clear Completed Confirmation Dialog */}
      <Dialog open={clearingCompleted} onOpenChange={setClearingCompleted}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Clear Completed Tasks</DialogTitle>
            <DialogDescription>
              This will remove all {completedTasks} completed tasks from your queue. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="mt-2 p-3 rounded-lg bg-slate-800/50 border border-slate-700">
            <div className="text-sm text-slate-300">
              Completed tasks will be permanently deleted.
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setClearingCompleted(false)}>
              <X className="w-4 h-4 mr-2" />
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                clearCompleted();
                setClearingCompleted(false);
              }}
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Clear Completed
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Node Details Panel - Slide-out from right */}
      {selectedNode && (
        <div className="fixed right-0 top-0 h-full w-80 bg-slate-900 border-l border-slate-700 shadow-xl z-50 overflow-y-auto">
          <div className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-slate-200">Node Details</h2>
              <Button 
                variant="ghost" 
                size="sm"
                onClick={() => setSelectedNode(null)}
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
            
            <div className="space-y-4">
              {/* Node Title */}
              <div className="p-3 rounded-lg bg-slate-800/50 border border-slate-700">
                <div className="text-xs text-slate-400 mb-1">Title</div>
                <div className="font-medium text-slate-200">{(selectedNode.data as {label?: string}).label || 'Unknown'}</div>
              </div>

              {/* Node Type */}
              <div className="p-3 rounded-lg bg-slate-800/50 border border-slate-700">
                <div className="text-xs text-slate-400 mb-1">Type / Role</div>
                <div className="text-slate-200">
                  {(selectedNode.data as {type?: string}).type || 'agent'}
                  {(selectedNode.data as {subtitle?: string}).subtitle && (
                    <span className="text-slate-400"> - {(selectedNode.data as {subtitle?: string}).subtitle}</span>
                  )}
                </div>
              </div>

              {/* Status */}
              <div className="p-3 rounded-lg bg-slate-800/50 border border-slate-700">
                <div className="text-xs text-slate-400 mb-1">Status</div>
                <div className="flex items-center gap-2">
                  <div className={`w-2.5 h-2.5 rounded-full ${
                    (selectedNode.data as {status?: string}).status === 'working' || (selectedNode.data as {status?: string}).status === 'running'
                      ? 'bg-yellow-400 animate-pulse'
                      : (selectedNode.data as {status?: string}).status === 'completed'
                      ? 'bg-green-400'
                      : (selectedNode.data as {status?: string}).status === 'failed'
                      ? 'bg-red-400'
                      : 'bg-slate-500'
                  }`} />
                  <span className="text-slate-200 capitalize">{(selectedNode.data as {status?: string}).status || 'idle'}</span>
                </div>
              </div>

                {/* Execution Time */}
              <div className="p-3 rounded-lg bg-slate-800/50 border border-slate-700">
                <div className="text-xs text-slate-400 mb-1">Execution Time</div>
                <div className="flex items-center gap-2 text-slate-200">
                  <Clock className="w-4 h-4 text-slate-400" />
                  <span>N/A</span>
                </div>
              </div>

              {/* Input Summary */}
              <div className="p-3 rounded-lg bg-slate-800/50 border border-slate-700">
                <div className="text-xs text-slate-400 mb-1">Input</div>
                <div className="text-sm text-slate-300">Task input data</div>
              </div>

              {/* Output Summary */}
              <div className="p-3 rounded-lg bg-slate-800/50 border border-slate-700">
                <div className="text-xs text-slate-400 mb-1">Output</div>
                <div className="text-sm text-slate-300">Pending execution...</div>
              </div>

              {/* Retry Button */}
              <Button 
                className="w-full"
                variant="outline"
                onClick={() => {
                  // Reset node status to pending
                  setNodes((nds) => 
                    nds.map((n) => 
                      n.id === selectedNode.id 
                        ? { ...n, data: { ...n.data, status: 'pending' } }
                        : n
                    )
                  );
                  setSelectedNode(null);
                }}
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Retry Node
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Wrapper component with ReactFlowProvider
export default function OrchestrationPage() {
  return (
    <ReactFlowProvider>
      <OrchestrationPageInner />
    </ReactFlowProvider>
  );
}