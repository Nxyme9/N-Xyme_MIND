"use client";

import { useState, useCallback, useEffect, useMemo, lazy, Suspense } from "react";
import type { Node, Edge } from "@xyflow/react";
import { useNodesState, useEdgesState, MarkerType, BackgroundVariant } from "@xyflow/react";

const ReactFlow = lazy(() => import("@xyflow/react").then(mod => ({ default: mod.ReactFlow })));
const Background = lazy(() => import("@xyflow/react").then(mod => ({ default: mod.Background })));
const Controls = lazy(() => import("@xyflow/react").then(mod => ({ default: mod.Controls })));
const MiniMap = lazy(() => import("@xyflow/react").then(mod => ({ default: mod.MiniMap })));
const Panel = lazy(() => import("@xyflow/react").then(mod => ({ default: mod.Panel })));
const ReactFlowProvider = lazy(() => import("@xyflow/react").then(mod => ({ default: mod.ReactFlowProvider })));
import "@xyflow/react/dist/style.css";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useMemorySearch, useMemoryStats, useMemoryWrite } from "@/hooks/useMemory";
import { useToast } from "@/context/ToastContext";
import { Maximize2, Minimize2 } from "lucide-react";
import { NoMemoriesState } from "@/components/ui/empty-state";

interface MemoryItem {
  id: string;
  content: string;
  type: string;
  trust: number;
  timestamp?: string;
  pinned?: boolean;
  tags?: string[];
  position?: { x: number; y: number };
}

function TrustMeter({ value }: { value: number }) {
  const getColor = (v: number) => {
    if (v >= 0.9) return "bg-green-500";
    if (v >= 0.7) return "bg-yellow-500";
    return "bg-red-500";
  };

  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full ${getColor(value)}`} style={{ width: `${value * 100}%` }} />
      </div>
      <span className="text-xs text-slate-400">{(value * 100).toFixed(0)}%</span>
    </div>
  );
}

function MemoryNode({ 
  node, 
  onClick, 
  onDoubleClick,
  onContextMenu,
  isSelected,
  scale,
  onDragStart
}: { 
  node: { id: string; label: string; type: string; x: number; y: number; tags?: string[] }; 
  onClick?: () => void;
  onDoubleClick?: () => void;
  onContextMenu?: (e: React.MouseEvent) => void;
  isSelected?: boolean;
  scale?: number;
  onDragStart?: (nodeId: string, offsetX: number, offsetY: number) => void;
}) {
  const isSemantic = node.type === "semantic";
  return (
    <div
      className={`absolute w-28 h-14 rounded-lg flex flex-col items-center justify-center text-xs font-medium shadow-md transition-all cursor-move select-none ${
        isSemantic
          ? "bg-slate-800 border-2 border-blue-500 text-blue-300"
          : "bg-slate-800 border-2 border-purple-500 text-purple-300"
      } ${isSelected ? "ring-2 ring-white scale-105" : ""}`}
      style={{ 
        left: node.x * (scale || 1), 
        top: node.y * (scale || 1),
        transform: `scale(${scale || 1})`,
        transformOrigin: 'center'
      }}
      onClick={onClick}
      onDoubleClick={onDoubleClick}
      onContextMenu={onContextMenu}
      onMouseDown={(e) => {
        if (onDragStart && e.button === 0) {
          const rect = e.currentTarget.getBoundingClientRect();
          onDragStart(node.id, e.clientX - rect.left, e.clientY - rect.top);
        }
      }}
    >
      <span className="truncate px-1">{node.label}</span>
      {node.tags && node.tags.length > 0 && (
        <div className="flex gap-1 mt-1 flex-wrap justify-center px-1">
          {node.tags.slice(0, 2).map((tag, i) => (
            <span key={i} className="text-[8px] px-1 py-0.5 bg-slate-700 rounded-full">
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function LoadingState() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
          <div className="animate-pulse space-y-3">
            <div className="h-4 bg-slate-700 rounded w-1/4"></div>
            <div className="h-6 bg-slate-700 rounded w-3/4"></div>
            <div className="h-3 bg-slate-700 rounded w-full"></div>
            <div className="h-3 bg-slate-700 rounded w-2/3"></div>
            <div className="flex gap-2">
              <div className="h-5 bg-slate-700 rounded w-16"></div>
              <div className="h-5 bg-slate-700 rounded w-16"></div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function CustomEmptyState({ hasQuery, onCreate }: { hasQuery: boolean; onCreate?: () => void }) {
  if (hasQuery) {
    return (
      <NoMemoriesState 
        hasSearchQuery={true} 
      />
    );
  }
  return (
    <NoMemoriesState 
      onCreate={onCreate} 
    />
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <div className="text-red-400 mb-2">Error loading memories</div>
      <div className="text-slate-500 text-sm mb-4">{message}</div>
      <Button variant="outline" size="sm" onClick={onRetry}>
        Retry
      </Button>
    </div>
  );
}

// Lazy-loaded ReactFlow graph component for React 19 compatibility
function MemoryGraphView({ isFullscreen, setIsFullscreen }: { isFullscreen: boolean; setIsFullscreen: (v: boolean) => void }) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  
  const { results: searchResults } = useMemorySearch("", 50);
  
  useEffect(() => {
    if (searchResults && searchResults.length > 0) {
      const memoryNodes = searchResults.slice(0, 6).map((r: { id?: string; content?: string; type?: string; source?: string }, idx: number) => ({
        id: r.id || `mem-${idx}`,
        position: { x: 100 + (idx % 3) * 150, y: 80 + Math.floor(idx / 3) * 120 },
        data: { label: (r.content || "").slice(0, 12) + "...", type: r.type || "semantic" },
        style: {
          background: r.type === "semantic" ? "#1e293b" : "#1e1b2e",
          border: `2px solid ${r.type === "semantic" ? "#3b82f6" : "#9333ea"}`,
          borderRadius: "8px",
          padding: "8px 12px",
          color: r.type === "semantic" ? "#93c5fd" : "#d8b4fe",
          width: 120,
        },
      }));
      
      const memoryEdges: Edge[] = memoryNodes.slice(0, -1).map((node: { id: string; data: { type?: string } }, idx: number) => ({
        id: `e-${node.id}-${memoryNodes[idx + 1].id}`,
        source: node.id,
        target: memoryNodes[idx + 1].id,
        style: { stroke: node.data.type === "semantic" ? "#3b82f6" : "#9333ea", strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: node.data.type === "semantic" ? "#3b82f6" : "#9333ea" },
      }));
      
      setNodes(memoryNodes);
      setEdges(memoryEdges);
    }
  }, [searchResults, setNodes, setEdges]);

  return (
    <div className={`relative ${isFullscreen ? 'fixed inset-0 z-50 bg-slate-900' : ''}`}>
      {isFullscreen && (
        <div className="absolute top-4 right-4 z-50">
          <Button variant="outline" size="sm" onClick={() => setIsFullscreen(false)}>
            <Minimize2 className="w-4 h-4 mr-2" />
            Exit Fullscreen (Esc)
          </Button>
        </div>
      )}
      <Suspense fallback={<div className="h-[300px] flex items-center justify-center text-slate-400">Loading graph...</div>}>
        <div className={`bg-slate-900 rounded-lg border border-slate-700 ${isFullscreen ? 'h-[calc(100vh-100px)]' : 'h-[300px]'}`}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView
            attributionPosition="bottom-left"
            proOptions={{ hideAttribution: true }}
          >
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#334155" />
            <Controls className="bg-slate-800 border-slate-700 text-slate-200" />
            <MiniMap
              nodeColor={(node) => node.data?.type === "semantic" ? "#3b82f6" : "#9333ea"}
              maskColor="rgba(15, 23, 42, 0.8)"
              className="bg-slate-800 border-slate-700"
              position="bottom-right"
            />
            <Panel position="top-right" className="bg-slate-800/90 border border-slate-700 p-2 rounded-lg">
              <div className="flex items-center gap-2 text-xs text-slate-300">
                <div className="flex items-center gap-1">
                  <div className="w-2.5 h-2.5 rounded bg-blue-500" />
                  <span>Semantic</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-2.5 h-2.5 rounded bg-purple-500" />
                  <span>Episodic</span>
                </div>
              </div>
            </Panel>
          </ReactFlow>
        </div>
      </Suspense>
    </div>
  );
}

export default function MemoryPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTab, setActiveTab] = useState<"semantic" | "episodic" | "timeline">("semantic");
  const [activeView, setActiveView] = useState<"graph" | "timeline">("graph");
  
  // Node selection state
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [contextMenu, setContextMenu] = useState<{ nodeId: string; x: number; y: number } | null>(null);
  const [tagFilter, setTagFilter] = useState<string>("");
  
  // CRUD state
  const [localMemories, setLocalMemories] = useState<MemoryItem[]>([]);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingMemory, setEditingMemory] = useState<MemoryItem | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [formData, setFormData] = useState({ content: "", kind: "semantic" as string, tags: "" });
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;
  
  // Sorting state
  const [sortBy, setSortBy] = useState<string>("date-newest");
  
  // Type filter state
  const [typeFilter, setTypeFilter] = useState<string>("all");

  // Fullscreen state
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Bulk select state
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkDeleteConfirmId, setBulkDeleteConfirmId] = useState<string | null>(null);
  
  // Edge labels toggle
  const [showEdgeLabels, setShowEdgeLabels] = useState(true);

  // Dragging state
  const [draggingNode, setDraggingNode] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const graphScale = 1;

  // ReactFlow state
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // Hooks
  const { results: searchResults, isLoading: searchLoading, isError: searchError, refetch: searchRefetch } = useMemorySearch(searchQuery, 50);
  const { totalMemories, isLoading: statsLoading } = useMemoryStats();
  const writeMemory = useMemoryWrite();
  const { addToast } = useToast();

  // Sync search results to local state when they change
  const [initialized, setInitialized] = useState(false);
  
  useEffect(() => {
    if (searchLoading || searchQuery !== "" || initialized) return;
    
    setInitialized(true);
    
    if (searchResults && searchResults.length > 0) {
      const apiMemories: MemoryItem[] = searchResults.map((r: any, idx: number) => ({
        id: r.id || `mem-${idx}`,
        content: r.content || r.content?.substring(0, 200) || "",
        type: r.type || r.source || "semantic",
        trust: r.score ?? r.trust ?? 0.8,
        pinned: false,
      }));
      setLocalMemories(apiMemories);
      setCurrentPage(1);
    } else {
      setLocalMemories([]);
    }
  }, [searchResults, searchLoading, searchQuery, initialized]);

  // Close context menu on outside click - runs anytime contextMenu changes
  useEffect(() => {
    if (!contextMenu) return;
    const handleClick = () => closeContextMenu();
    window.addEventListener("click", handleClick);
    return () => window.removeEventListener("click", handleClick);
  }, [contextMenu]);

  // Local memories for CRUD operations
  const memories = localMemories;

  // Filtered memories by type
  const filteredMemories = memories.filter((m) => {
    // Type filter
    if (typeFilter !== "all" && m.type !== typeFilter) return false;
    // Tab filter
    if (activeTab === "semantic") return m.type === "semantic";
    if (activeTab === "episodic") return m.type === "episodic";
    return true;
  });

  // Sorted memories
  const sortedMemories = [...filteredMemories].sort((a, b) => {
    // Pinned always first
    if (a.pinned && !b.pinned) return -1;
    if (!a.pinned && b.pinned) return 1;
    
    switch (sortBy) {
      case "date-newest":
        return new Date(b.timestamp || 0).getTime() - new Date(a.timestamp || 0).getTime();
      case "date-oldest":
        return new Date(a.timestamp || 0).getTime() - new Date(b.timestamp || 0).getTime();
      case "name-az":
        return a.content.localeCompare(b.content);
      case "name-za":
        return b.content.localeCompare(a.content);
      case "trust-high":
        return b.trust - a.trust;
      case "trust-low":
        return a.trust - b.trust;
      default:
        return 0;
    }
  });

  // Calculate stats
  const avgTrust = memories.length > 0
    ? memories.reduce((acc, m) => acc + m.trust, 0) / memories.length
    : (totalMemories > 0 ? 0.85 : 0.90);

  // Pagination
  const totalPages = Math.ceil(sortedMemories.length / itemsPerPage);
  const start = (currentPage - 1) * itemsPerPage + 1;
  const end = Math.min(currentPage * itemsPerPage, sortedMemories.length);
  const paginatedMemories = sortedMemories.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  // Generate memory nodes from real data (no hardcoded fallback)
  const memoryNodes = memories.slice(0, 6).map((m, idx) => ({
    id: m.id,
    label: m.content.slice(0, 12) + (m.content.length > 12 ? "..." : ""),
    type: m.type,
    x: m.position?.x ?? (100 + (idx % 3) * 150),
    y: m.position?.y ?? (80 + Math.floor(idx / 3) * 120),
    tags: m.tags || [],
  }));

  // Generate ReactFlow nodes and edges from memory data
  const flowNodes: Node[] = useMemo(() => {
    return memoryNodes.map((node, idx) => ({
      id: node.id,
      position: { x: node.x, y: node.y },
      data: { 
        label: node.label, 
        type: node.type,
        tags: node.tags 
      },
      style: {
        background: node.type === "semantic" ? "#1e293b" : "#1e1b2e",
        border: `2px solid ${node.type === "semantic" ? "#3b82f6" : "#9333ea"}`,
        borderRadius: "8px",
        padding: "8px 12px",
        color: node.type === "semantic" ? "#93c5fd" : "#d8b4fe",
        width: 120,
      },
    }));
  }, [memoryNodes]);

  const flowEdges: Edge[] = useMemo(() => {
    const labels = ["related_to", "parent_of", "similar_to", "depends_on", "references"];
    return memoryNodes.slice(0, -1).map((node, idx) => ({
      id: `e-${node.id}-${memoryNodes[idx + 1].id}`,
      source: node.id,
      target: memoryNodes[idx + 1].id,
      label: showEdgeLabels ? labels[idx % labels.length] : undefined,
      style: { 
        stroke: node.type === "semantic" ? "#3b82f6" : "#9333ea", 
        strokeWidth: 2 
      },
      markerEnd: { 
        type: MarkerType.ArrowClosed,
        color: node.type === "semantic" ? "#3b82f6" : "#9333ea"
      },
      labelStyle: { fill: "#94a3b8", fontSize: 10 },
      labelBackgroundColor: "#1e293b",
      labelBackgroundPadding: [3, 3] as [number, number],
    }));
  }, [memoryNodes, showEdgeLabels]);

  // Sync flow nodes/edges when memory data changes
  useEffect(() => {
    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [flowNodes, flowEdges, setNodes, setEdges]);

  // Extract all unique tags for filtering
  const allTags = [...new Set(memories.flatMap(m => m.tags || []))];
  
  // Filtered memories by tag
  const tagFilteredMemories = tagFilter 
    ? memories.filter(m => m.tags?.includes(tagFilter))
    : memories;

  // Handlers for keyboard shortcuts and UI
  const handleSearch = useCallback(() => {
    searchRefetch();
    setCurrentPage(1);
  }, [searchRefetch]);

  const handleCreate = useCallback(() => {
    setEditingMemory(null);
    setFormData({ content: "", kind: "semantic", tags: "" });
    setIsFormOpen(true);
  }, []);

  const handleEdit = useCallback((memory: MemoryItem) => {
    setEditingMemory(memory);
    setFormData({ 
      content: memory.content, 
      kind: memory.type,
      tags: memory.tags?.join(", ") || ""
    });
    setIsFormOpen(true);
  }, []);

  const confirmDelete = useCallback(() => {
    if (deleteConfirmId) {
      setLocalMemories((prev) => prev.filter((m) => m.id !== deleteConfirmId));
      setDeleteConfirmId(null);
      addToast("Memory deleted successfully", "success");
    }
  }, [deleteConfirmId, addToast]);

  // Bulk select handlers
  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const selectAll = useCallback(() => {
    if (selectedIds.size === paginatedMemories.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(paginatedMemories.map((m) => m.id)));
    }
  }, [paginatedMemories, selectedIds.size]);

  const confirmBulkDelete = useCallback(() => {
    if (selectedIds.size > 0) {
      setLocalMemories((prev) => prev.filter((m) => !selectedIds.has(m.id)));
      setSelectedIds(new Set());
      setBulkDeleteConfirmId(null);
      addToast(`${selectedIds.size} memories deleted`, "success");
    }
  }, [selectedIds, addToast]);

  const handlePin = useCallback((id: string) => {
    setLocalMemories((prev) =>
      prev.map((m) => {
        if (m.id === id) {
          const newPinned = !m.pinned;
          addToast(newPinned ? "Memory pinned" : "Memory unpinned", "success");
          return { ...m, pinned: newPinned };
        }
        return m;
      })
    );
  }, [addToast]);

  // Keyboard shortcuts - runs after handlers are defined
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Close context menu on Escape
      if (e.key === "Escape" && contextMenu) {
        closeContextMenu();
        return;
      }
      // Escape to exit fullscreen
      if (e.key === "Escape" && isFullscreen) {
        setIsFullscreen(false);
        return;
      }
      // Ctrl+K: Focus search
      if (e.ctrlKey && e.key === "k") {
        e.preventDefault();
        document.querySelector<HTMLInputElement>('input[placeholder*="Search"]')?.focus();
      }
      // Ctrl+N: New memory
      if (e.ctrlKey && e.key === "n") {
        e.preventDefault();
        handleCreate();
      }
      // Delete selected node
      if (e.key === "Delete" && selectedNodeId) {
        setDeleteConfirmId(selectedNodeId);
      }
      // Arrow keys navigation
      if (e.key === "ArrowRight" || e.key === "ArrowLeft" || e.key === "ArrowUp" || e.key === "ArrowDown") {
        e.preventDefault();
        const currentIdx = memoryNodes.findIndex(n => n.id === selectedNodeId);
        if (currentIdx >= 0) {
          let newIdx = currentIdx;
          if (e.key === "ArrowRight" || e.key === "ArrowDown") {
            newIdx = Math.min(currentIdx + 1, memoryNodes.length - 1);
          } else {
            newIdx = Math.max(currentIdx - 1, 0);
          }
          setSelectedNodeId(memoryNodes[newIdx]?.id || null);
        }
      }
      // F11 or Ctrl+Shift+F: Toggle fullscreen
      if ((e.key === "F11") || (e.ctrlKey && e.shiftKey && e.key === "F")) {
        e.preventDefault();
        setIsFullscreen(prev => !prev);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [contextMenu, selectedNodeId, memoryNodes, handleCreate, isFullscreen]);

  // Handle node drag
  const handleDragStart = useCallback((nodeId: string, offsetX: number, offsetY: number) => {
    setDraggingNode(nodeId);
    setDragOffset({ x: offsetX, y: offsetY });
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (draggingNode) {
      const container = (e.currentTarget as HTMLElement).closest('.graph-container');
      if (container) {
        const rect = container.getBoundingClientRect();
        const newX = (e.clientX - rect.left - dragOffset.x) / graphScale;
        const newY = (e.clientY - rect.top - dragOffset.y) / graphScale;
        setLocalMemories(prev => prev.map(m => 
          m.id === draggingNode ? { ...m, position: { x: Math.max(0, newX), y: Math.max(0, newY) } } : m
        ));
      }
    }
  }, [draggingNode, dragOffset, graphScale]);

  const handleMouseUp = useCallback(() => {
    setDraggingNode(null);
  }, []);

  // Context menu handlers
  const handleNodeContextMenu = useCallback((e: React.MouseEvent, nodeId: string) => {
    e.preventDefault();
    setContextMenu({ nodeId, x: e.clientX, y: e.clientY });
  }, []);

  const closeContextMenu = useCallback(() => {
    setContextMenu(null);
  }, []);

  // Duplicate memory
  const handleDuplicate = useCallback((id: string) => {
    const memory = memories.find(m => m.id === id);
    if (memory) {
      const newMemory: MemoryItem = {
        ...memory,
        id: `mem-${Date.now()}`,
        content: `${memory.content} (copy)`,
        pinned: false,
      };
      setLocalMemories(prev => [newMemory, ...prev]);
    }
    closeContextMenu();
  }, [memories, closeContextMenu]);

  const handleSubmitForm = useCallback(async () => {
    if (!formData.content.trim()) return;

    const tags = formData.tags
      .split(",")
      .map(t => t.trim())
      .filter(t => t.length > 0);

    if (editingMemory) {
      // Update locally (full CRUD would need an update API)
      setLocalMemories((prev) =>
        prev.map((m) =>
          m.id === editingMemory.id
            ? { ...m, content: formData.content, type: formData.kind, tags }
            : m
        )
      );
      addToast("Memory updated successfully", "success");
    } else {
      // Create new memory - write to API
      const newMemory: MemoryItem = {
        id: `mem-${Date.now()}`,
        content: formData.content,
        type: formData.kind,
        trust: 0.8,
        pinned: false,
        tags,
        timestamp: new Date().toISOString(),
      };

      // Optimistically add to local state
      setLocalMemories((prev) => [newMemory, ...prev]);

      // Write to API
      try {
        await writeMemory.mutateAsync({
          content: formData.content,
          kind: formData.kind,
        });
        addToast("Memory created successfully", "success");
      } catch (error) {
        console.error("Failed to write memory to API:", error);
        addToast("Failed to create memory", "error");
      }
    }

    setIsFormOpen(false);
    setEditingMemory(null);
    setFormData({ content: "", kind: "semantic", tags: "" });
  }, [formData, editingMemory, writeMemory, addToast]);

  if (searchLoading && memories.length === 0) {
    return (
      <div className="container mx-auto py-8">
        <h1 className="text-3xl font-bold mb-6">Memory Visualization</h1>
        <LoadingState />
      </div>
    );
  }

  if (searchError && memories.length === 0) {
    return (
      <div className="container mx-auto py-8">
        <h1 className="text-3xl font-bold mb-6">Memory Visualization</h1>
        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="pt-6">
            <ErrorState message="Failed to load memories" onRetry={() => searchRefetch()} />
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">Memory Visualization</h1>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-lg">
            {totalMemories > 0 ? totalMemories : memories.length} Memories
          </Badge>
          <Badge variant="default" className="bg-blue-500 border-0">
            Avg Trust: {(avgTrust * 100).toFixed(0)}%
          </Badge>
        </div>
      </div>

      {/* Search + Create */}
      <Card className="mb-6 bg-slate-800/50 border-slate-700">
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-2 items-center">
            <Input
              placeholder="Search memories... (Ctrl+K)"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              className="flex-1 min-w-[200px] bg-slate-800 border-slate-600 text-slate-200 placeholder:text-slate-500"
            />
            {/* Sort dropdown */}
            <select
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value);
                setCurrentPage(1);
              }}
              className="bg-slate-800 border border-slate-600 rounded px-2 py-1.5 text-sm text-slate-200"
            >
              <option value="date-newest">Date (Newest)</option>
              <option value="date-oldest">Date (Oldest)</option>
              <option value="name-az">Name (A-Z)</option>
              <option value="name-za">Name (Z-A)</option>
              <option value="trust-high">Trust (High)</option>
              <option value="trust-low">Trust (Low)</option>
            </select>
            {/* Type filter dropdown */}
            <select
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="bg-slate-800 border border-slate-600 rounded px-2 py-1.5 text-sm text-slate-200"
            >
              <option value="all">All Types</option>
              <option value="semantic">Semantic</option>
              <option value="episodic">Episodic</option>
            </select>
            {/* Tag filter dropdown */}
            {allTags.length > 0 && (
              <select
                value={tagFilter}
                onChange={(e) => setTagFilter(e.target.value)}
                className="bg-slate-800 border border-slate-600 rounded px-2 py-1.5 text-sm text-slate-200"
              >
                <option value="">All Tags</option>
                {allTags.map(tag => (
                  <option key={tag} value={tag}>{tag}</option>
                ))}
              </select>
            )}
            <Button onClick={handleSearch}>Search</Button>
            <Dialog open={isFormOpen} onOpenChange={setIsFormOpen}>
              <DialogTrigger asChild>
                <Button variant="default" onClick={handleCreate}>
                  + New Memory
                </Button>
              </DialogTrigger>
              <DialogContent className="bg-slate-800 border-slate-700">
                <DialogHeader>
                  <DialogTitle>
                    {editingMemory ? "Edit Memory" : "Create New Memory"}
                  </DialogTitle>
                  <DialogDescription>
                    {editingMemory
                      ? "Update the memory content below"
                      : "Add a new memory to your memory store"}
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <label className="text-sm text-slate-400">Content</label>
                    <Input
                      value={formData.content}
                      onChange={(e) => setFormData((prev) => ({ ...prev, content: e.target.value }))}
                      placeholder="Enter memory content..."
                      className="bg-slate-800 border-slate-600 text-slate-200"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm text-slate-400">Type</label>
                    <div className="flex gap-2">
                      <Button
                        variant={formData.kind === "semantic" ? "default" : "outline"}
                        size="sm"
                        onClick={() => setFormData((prev) => ({ ...prev, kind: "semantic" }))}
                      >
                        Semantic
                      </Button>
                      <Button
                        variant={formData.kind === "episodic" ? "default" : "outline"}
                        size="sm"
                        onClick={() => setFormData((prev) => ({ ...prev, kind: "episodic" }))}
                      >
                        Episodic
                      </Button>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm text-slate-400">Tags (comma-separated)</label>
                    <Input
                      value={formData.tags}
                      onChange={(e) => setFormData((prev) => ({ ...prev, tags: e.target.value }))}
                      placeholder="e.g., important, work, idea"
                      className="bg-slate-800 border-slate-600 text-slate-200"
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setIsFormOpen(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleSubmitForm} disabled={!formData.content.trim()}>
                    {editingMemory ? "Update" : "Create"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </CardContent>
      </Card>

      {/* Memory Visualization */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Memory Visualization</CardTitle>
            <div className="flex items-center gap-2">
              {/* View toggle */}
              <div className="flex rounded-lg border border-slate-600 overflow-hidden">
                <button
                  onClick={() => setActiveView("graph")}
                  className={`px-3 py-1 text-sm ${activeView === "graph" ? "bg-blue-600 text-white" : "bg-slate-800 text-slate-300 hover:bg-slate-700"}`}
                >
                  Graph
                </button>
                <button
                  onClick={() => setActiveView("timeline")}
                  className={`px-3 py-1 text-sm ${activeView === "timeline" ? "bg-blue-600 text-white" : "bg-slate-800 text-slate-300 hover:bg-slate-700"}`}
                >
                  Timeline
                </button>
              </div>
              {/* Fullscreen button */}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsFullscreen(!isFullscreen)}
                title={isFullscreen ? "Exit Fullscreen (Esc)" : "Fullscreen (Ctrl+Shift+F)"}
              >
                {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
              </Button>
              {/* Edge labels toggle */}
              <Button
                variant={showEdgeLabels ? "default" : "outline"}
                size="sm"
                onClick={() => setShowEdgeLabels(!showEdgeLabels)}
                title={showEdgeLabels ? "Hide edge labels" : "Show edge labels"}
              >
                Labels
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {activeView === "graph" ? (
            <MemoryGraphView isFullscreen={isFullscreen} setIsFullscreen={setIsFullscreen} />
          ) : (
            <div className="space-y-3 max-h-[400px] overflow-y-auto">
              {tagFilteredMemories.length === 0 ? (
                <CustomEmptyState hasQuery={searchQuery.length > 0} />
              ) : (
                <>
                  {/* Group by date */}
                  {["Today", "Yesterday", "This Week", "Earlier"].map(group => {
                    const now = new Date();
                    const filtered = tagFilteredMemories.filter(m => {
                      if (!m.timestamp) return group === "Earlier";
                      const d = new Date(m.timestamp);
                      const diff = now.getTime() - d.getTime();
                      const days = diff / (1000 * 60 * 60 * 24);
                      if (group === "Today") return days < 1;
                      if (group === "Yesterday") return days >= 1 && days < 2;
                      if (group === "This Week") return days >= 2 && days < 7;
                      return days >= 7;
                    });
                    if (filtered.length === 0) return null;
                    return (
                      <div key={group}>
                        <h3 className="text-sm font-medium text-slate-400 mb-2">{group}</h3>
                        {filtered.map(memory => (
                          <Card key={memory.id} className="bg-slate-800/30 border-slate-700 mb-2">
                            <CardContent className="py-3">
                              <div className="flex items-start justify-between">
                                <div className="flex-1">
                                  <p className="text-sm text-slate-200 line-clamp-2">{memory.content}</p>
                                  <div className="flex items-center gap-2 mt-2">
                                    <Badge variant="outline" className="text-xs">{memory.type}</Badge>
                                    {memory.tags?.map(tag => (
                                      <Badge key={tag} variant="secondary" className="text-xs bg-slate-700">{tag}</Badge>
                                    ))}
                                    <span className="text-xs text-slate-500">
                                      {memory.timestamp ? new Date(memory.timestamp).toLocaleDateString() : ""}
                                    </span>
                                  </div>
                                </div>
                                <div className="flex items-center gap-1 ml-2">
                                  <Button variant="ghost" size="sm" onClick={() => handleEdit(memory)} className="h-6 px-2">✏️</Button>
                                  <Button variant="ghost" size="sm" onClick={() => setDeleteConfirmId(memory.id)} className="h-6 px-2 text-red-400">🗑️</Button>
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    );
                  })}
                </>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tab Buttons for Memory Types */}
      <div className="mb-4 flex gap-2 items-center">
        <Button
          variant={activeTab === "semantic" ? "default" : "outline"}
          onClick={() => {
            setActiveTab("semantic");
            setCurrentPage(1);
          }}
        >
          Semantic ({filteredMemories.filter((m) => m.type === "semantic").length})
        </Button>
        <Button
          variant={activeTab === "episodic" ? "default" : "outline"}
          onClick={() => {
            setActiveTab("episodic");
            setCurrentPage(1);
          }}
        >
          Episodic ({filteredMemories.filter((m) => m.type === "episodic").length})
        </Button>
        {filteredMemories.length > 0 && (
          <div className="ml-auto flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={selectAll}
            >
              {selectedIds.size === paginatedMemories.length ? "Deselect All" : "Select All"}
            </Button>
            {selectedIds.size > 0 && (
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setBulkDeleteConfirmId("bulk")}
              >
                Delete Selected ({selectedIds.size})
              </Button>
            )}
          </div>
        )}
      </div>

      {/* Memory List */}
      {filteredMemories.length === 0 ? (
        <CustomEmptyState hasQuery={searchQuery.length > 0} onCreate={handleCreate} />
      ) : (
        <>
          {activeTab === "semantic" ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {paginatedMemories.map((memory) => (
                <Card key={memory.id} className="bg-slate-800/50 border-slate-700">
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(memory.id)}
                          onChange={() => toggleSelect(memory.id)}
                          className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-blue-500 focus:ring-blue-500"
                        />
                        <Badge variant="outline" className="text-xs border-slate-600 text-slate-300">
                          {memory.type}
                        </Badge>
                        {memory.pinned && (
                          <Badge variant="default" className="bg-yellow-500 border-0 text-xs">
                            Pinned
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handlePin(memory.id)}
                          className="h-6 px-2"
                        >
                          {memory.pinned ? "📌" : "📍"}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEdit(memory)}
                          className="h-6 px-2"
                        >
                          ✏️
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setDeleteConfirmId(memory.id)}
                          className="h-6 px-2 text-red-400 hover:text-red-300"
                        >
                          🗑️
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-slate-200">{memory.content}</p>
                    {memory.tags && memory.tags.length > 0 && (
                      <div className="flex gap-1 mt-2 flex-wrap">
                        {memory.tags.map(tag => (
                          <Badge key={tag} variant="secondary" className="text-xs bg-slate-700">{tag}</Badge>
                        ))}
                      </div>
                    )}
                    <div className="mt-2">
                      <TrustMeter value={memory.trust} />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <div className="space-y-4">
              {paginatedMemories.map((memory) => (
                <Card key={memory.id} className="bg-slate-800/50 border-slate-700">
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(memory.id)}
                          onChange={() => toggleSelect(memory.id)}
                          className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-blue-500 focus:ring-blue-500"
                        />
                        <Badge variant="secondary" className="text-xs bg-slate-700 text-slate-200">
                          episodic
                        </Badge>
                        {memory.pinned && (
                          <Badge variant="default" className="bg-yellow-500 border-0 text-xs">
                            Pinned
                          </Badge>
                        )}
                        <span className="text-xs text-slate-400">
                          {memory.timestamp ? new Date(memory.timestamp).toLocaleString() : "Unknown"}
                        </span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handlePin(memory.id)}
                          className="h-6 px-2"
                        >
                          {memory.pinned ? "📌" : "📍"}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEdit(memory)}
                          className="h-6 px-2"
                        >
                          ✏️
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setDeleteConfirmId(memory.id)}
                          className="h-6 px-2 text-red-400 hover:text-red-300"
                        >
                          🗑️
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="flex items-center justify-between">
                    <p className="text-sm text-slate-200 flex-1">{memory.content}</p>
                    <TrustMeter value={memory.trust} />
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-6">
              <Button
                variant="outline"
                size="sm"
                disabled={currentPage === 1}
                onClick={() => setCurrentPage((p) => p - 1)}
              >
                Previous
              </Button>
              <span className="text-sm text-slate-400">
                Showing {start}-{end} of {sortedMemories.length}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}

      {/* Delete Confirmation Modal */}
      <Dialog open={!!deleteConfirmId} onOpenChange={(open) => !open && setDeleteConfirmId(null)}>
        <DialogContent className="bg-slate-800 border-slate-700">
          <DialogHeader>
            <DialogTitle>Delete Memory?</DialogTitle>
            <DialogDescription>
              This action cannot be undone. This memory will be permanently deleted.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirmId(null)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={confirmDelete}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Bulk Delete Confirmation Modal */}
      <Dialog open={!!bulkDeleteConfirmId} onOpenChange={(open) => !open && setBulkDeleteConfirmId(null)}>
        <DialogContent className="bg-slate-800 border-slate-700">
          <DialogHeader>
            <DialogTitle>Delete {selectedIds.size} Memories?</DialogTitle>
            <DialogDescription>
              This action cannot be undone. These {selectedIds.size} memories will be permanently deleted.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setBulkDeleteConfirmId(null)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={confirmBulkDelete}>
              Delete {selectedIds.size} Memories
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Context Menu */}
      {contextMenu && (
        <div 
          className="fixed bg-slate-800 border border-slate-600 rounded-lg shadow-xl py-1 z-50"
          style={{ left: contextMenu.x, top: contextMenu.y }}
        >
          <button
            onClick={() => {
              const mem = memories.find(m => m.id === contextMenu.nodeId);
              if (mem) handleEdit(mem);
              closeContextMenu();
            }}
            className="w-full px-4 py-2 text-left text-sm text-slate-200 hover:bg-slate-700"
          >
            ✏️ Edit
          </button>
          <button
            onClick={() => {
              handlePin(contextMenu.nodeId);
              closeContextMenu();
            }}
            className="w-full px-4 py-2 text-left text-sm text-slate-200 hover:bg-slate-700"
          >
            {memories.find(m => m.id === contextMenu.nodeId)?.pinned ? "📌 Unpin" : "📍 Pin"}
          </button>
          <button
            onClick={() => handleDuplicate(contextMenu.nodeId)}
            className="w-full px-4 py-2 text-left text-sm text-slate-200 hover:bg-slate-700"
          >
            📋 Duplicate
          </button>
          <button
            onClick={() => {
              setDeleteConfirmId(contextMenu.nodeId);
              closeContextMenu();
            }}
            className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-slate-700"
          >
            🗑️ Delete
          </button>
        </div>
      )}

      {/* Export/Import buttons in header */}
      <div className="fixed bottom-4 right-4 flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            const data = JSON.stringify(memories, null, 2);
            const blob = new Blob([data], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "memories.json";
            a.click();
            URL.revokeObjectURL(url);
          }}
          className="text-xs"
        >
          📥 JSON
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            const csv = [
              ["id", "content", "type", "trust", "pinned", "tags", "timestamp"].join(","),
              ...memories.map(m => [
                m.id,
                `"${m.content.replace(/"/g, '""')}"`,
                m.type,
                m.trust,
                m.pinned,
                `"${(m.tags || []).join(";")}"`,
                m.timestamp || ""
              ].join(","))
            ].join("\n");
            const blob = new Blob([csv], { type: "text/csv" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "memories.csv";
            a.click();
            URL.revokeObjectURL(url);
          }}
          className="text-xs"
        >
          📥 CSV
        </Button>
        <input
          type="file"
          accept=".json"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) {
              const reader = new FileReader();
              reader.onload = (ev) => {
                try {
                  const imported = JSON.parse(ev.target?.result as string);
                  if (Array.isArray(imported)) {
                    setLocalMemories(imported);
                  }
                } catch (err) {
                  console.error("Failed to import:", err);
                }
              };
              reader.readAsText(file);
            }
          }}
          className="hidden"
          id="import-file"
        />
        <Button
          variant="outline"
          size="sm"
          onClick={() => document.getElementById("import-file")?.click()}
          className="text-xs"
        >
          📤 Import
        </Button>
      </div>
    </div>
  );
}
