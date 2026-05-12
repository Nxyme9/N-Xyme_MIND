"use client";

import { useState, useEffect, useRef } from "react";
import { useAgentStore } from "@/stores/useAgentStore";
import { useMCPStore } from "@/stores/useMCPStore";
import { useTaskStore } from "@/stores/useTaskStore";
import { useAgentStatus, useMCPStatus } from "@/hooks/useSystemStatus";
import { 
  Settings, 
  Code2, 
  Database, 
  Brain, 
  Cpu, 
  Network, 
  Terminal,
  Key,
  Globe,
  Shield,
  Zap,
  Palette,
  Bell,
  Monitor,
  HardDrive,
  CheckCircle,
  XCircle,
  AlertCircle,
  User,
  Upload,
  Download,
  Upload as ImportIcon,
  Trash2,
  RefreshCw,
  FileText,
  Mail,
  Volume2,
  Keyboard,
  Info,
  ExternalLink,
  HelpCircle,
  Eye,
  EyeOff,
  Plus,
  Copy
} from "lucide-react";

export default function SettingsPage() {
  const agents = useAgentStore((state) => state.agents);
  const connections = useMCPStore((state) => state.connections);
  const tasks = useTaskStore((state) => state.tasks);
  
  // Load initial settings from localStorage
const getInitialSettings = () => {
  if (typeof window === "undefined") return {};
  const saved = localStorage.getItem("settings");
  if (saved) {
    try {
      return JSON.parse(saved);
    } catch {
      return {};
    }
  }
  return {};
};

const initialSettings = getInitialSettings();

const [activeTab, setActiveTab] = useState("system");
const [aiProvider, setAiProvider] = useState("opencode");
const [autoRoute, setAutoRoute] = useState(initialSettings.autoRoute ?? true);
const [memoryEnabled, setMemoryEnabled] = useState(initialSettings.memoryEnabled ?? true);
const [developerMode, setDeveloperMode] = useState(initialSettings.developerMode ?? false);
const [verboseLogging, setVerboseLogging] = useState(initialSettings.verboseLogging ?? false);
const [selectedTheme, setSelectedTheme] = useState(initialSettings.selectedTheme ?? "dark");

// System tab state
const [systemVersion, setSystemVersion] = useState("v1.0.0");
const [systemUptime, setSystemUptime] = useState("00:00:00");
const [cpuUsage, setCpuUsage] = useState(0);
const [memoryUsage, setMemoryUsage] = useState(0);
const [toast, setToast] = useState<string | null>(null);

// Agents tab state - use real data from hook
const { agents: realAgents } = useAgentStatus();
const [agentList, setAgentList] = useState<Array<{ id: string; name: string; role: string; enabled: boolean }>>([]);

// Sync agentList with real data when it loads
useEffect(() => {
  if (realAgents.length > 0) {
    setAgentList(realAgents.map((agent) => ({
      id: agent.id,
      name: agent.name,
      role: agent.role || "Agent",
      enabled: agent.status !== "error",
    })));
  }
}, [realAgents]);
const [showAddAgentForm, setShowAddAgentForm] = useState(false);
const [newAgentName, setNewAgentName] = useState("");
const [newAgentRole, setNewAgentRole] = useState("");
const [newAgentModel, setNewAgentModel] = useState("");

// MCP tab state - use real data from hook
const { connections: realConnections } = useMCPStatus();
const [mcpList, setMcpList] = useState<Array<{ id: string; name: string; type: string; status: string }>>([]);

// Sync mcpList with real data when it loads
useEffect(() => {
  if (realConnections.length > 0) {
    setMcpList(realConnections.map((conn) => ({
      id: conn.name.toLowerCase().replace(/\s+/g, "_"),
      name: conn.name,
      type: conn.name.toLowerCase().replace(/\s+/g, "-"),
      status: conn.status,
    })));
  }
}, [realConnections]);
const [showAddMcpForm, setShowAddMcpForm] = useState(false);
const [newMcpName, setNewMcpName] = useState("");
const [newMcpType, setNewMcpType] = useState("");

// Routing tab state
const [providerPriority, setProviderPriority] = useState([
  { id: "opencode", name: "OpenCode", enabled: true },
  { id: "anthropic", name: "Anthropic", enabled: true },
  { id: "openai", name: "OpenAI", enabled: true },
  { id: "local", name: "Local (GGUF)", enabled: false },
]);
const [fallbackEnabled, setFallbackEnabled] = useState(true);
const [costLimit, setCostLimit] = useState(10);

// Memory tab state
const [memoryRetention, setMemoryRetention] = useState("30");
const [autoCleanup, setAutoCleanup] = useState(true);
const [memoryCompression, setMemoryCompression] = useState(false);

// Appearance tab state
const [selectedFont, setSelectedFont] = useState("Inter");
const [accentColor, setAccentColor] = useState("blue");
const [compactMode, setCompactMode] = useState(false);
const [animationsEnabled, setAnimationsEnabled] = useState(true);

// Account state
const [profileName, setProfileName] = useState(initialSettings.profileName ?? "");
const [profileEmail, setProfileEmail] = useState(initialSettings.profileEmail ?? "");
const [avatarUrl, setAvatarUrl] = useState(initialSettings.avatarUrl ?? "");

// Notification state
const [desktopNotifications, setDesktopNotifications] = useState(initialSettings.desktopNotifications ?? true);
const [emailNotifications, setEmailNotifications] = useState(initialSettings.emailNotifications ?? false);
const [soundNotifications, setSoundNotifications] = useState(initialSettings.soundNotifications ?? true);
const [notificationFrequency, setNotificationFrequency] = useState(initialSettings.notificationFrequency ?? "instant");
const [slackNotifications, setSlackNotifications] = useState(initialSettings.slackNotifications ?? false);

// Keyboard shortcuts state
interface Shortcut {
  id: string;
  action: string;
  key: string;
}

const defaultShortcuts: Shortcut[] = [
  { id: "newTask", action: "New Task", key: "Ctrl+N" },
  { id: "search", action: "Search", key: "Ctrl+K" },
  { id: "settings", action: "Settings", key: "Ctrl+," },
  { id: "healthCheck", action: "Run Health Check", key: "Ctrl+H" },
  { id: "toggleDev", action: "Toggle Dev Mode", key: "Ctrl+Shift+D" },
];
const [shortcuts, setShortcuts] = useState<Shortcut[]>(initialSettings.shortcuts ?? defaultShortcuts);
const [editingShortcut, setEditingShortcut] = useState<string | null>(null);
const [editKey, setEditKey] = useState("");

// API Keys state
interface ApiKey {
  id: string;
  name: string;
  key: string;
  provider: string;
  createdAt: string;
  permission: "read-only" | "full-access";
  usage?: {
    callsThisMonth: number;
    tokensUsed: number;
    lastUsed: string;
  };
}

const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);

// Fetch API keys from backend
useEffect(() => {
  async function fetchApiKeys() {
    try {
      const response = await fetch('/api/backend/api-keys');
      if (response.ok) {
        const data = await response.json();
        if (data.keys && data.keys.length > 0) {
          setApiKeys(data.keys);
        }
        // If no keys from API, keep empty (user must add their own)
      }
    } catch (error) {
      console.error('Failed to fetch API keys:', error);
      // Keep empty on error - user must add their own keys
    }
  }
  fetchApiKeys();
}, []);
const [visibleKeys, setVisibleKeys] = useState<Set<string>>(new Set());
const [showAddKeyModal, setShowAddKeyModal] = useState(false);
const [newKeyName, setNewKeyName] = useState("");
const [newKeyValue, setNewKeyValue] = useState("");
const [newKeyProvider, setNewKeyProvider] = useState("");
const [newKeyPermission, setNewKeyPermission] = useState<"read-only" | "full-access">("full-access");

// Confirm dialog state
const [showConfirmDialog, setShowConfirmDialog] = useState(false);
const [confirmAction, setConfirmAction] = useState<(() => void) | null>(null);
const [confirmMessage, setConfirmMessage] = useState("");

// Health check handler
const runHealthCheck = async (level: string) => {
  try {
    const response = await fetch('/api/backend/health', { method: 'GET' });
    const data = await response.json();
    if (response.ok) {
      const status = data.status || 'unknown';
      const checks = data.checks ? `Orchestration: ${data.backend?.orchestration ? 'OK' : 'Failed'}
MCP: ${data.checks?.mcp ? 'OK' : 'Failed'}
API: ${data.checks?.settings ? 'OK' : 'Failed'}
Version: ${data.version || '1.0.0'}` : '';
      showToast(`Health Check Result: ${status.toUpperCase()}\n\n${checks}`);
    } else {
      showToast('Health check failed to return valid data');
    }
  } catch (error) {
    console.error('Health check failed:', error);
    showToast(`Health check failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
};

// Developer tools handler
const runDevTool = (tool: string) => {
  showToast(`${tool} opened.\n\nCheck console for details.`);
};

// Persist settings to localStorage
useEffect(() => {
  localStorage.setItem("settings", JSON.stringify({
    autoRoute,
    memoryEnabled,
    developerMode,
    verboseLogging,
    selectedTheme,
    profileName,
    profileEmail,
    avatarUrl,
    desktopNotifications,
    emailNotifications,
    soundNotifications,
    notificationFrequency,
    shortcuts,
    slackNotifications
  }));
}, [autoRoute, memoryEnabled, developerMode, verboseLogging, selectedTheme, profileName, profileEmail, avatarUrl, desktopNotifications, emailNotifications, soundNotifications, notificationFrequency, shortcuts, slackNotifications]);

// System uptime calculation
const startTimeRef = useRef(Date.now());
useEffect(() => {
  const interval = setInterval(() => {
    const elapsed = Math.floor((Date.now() - startTimeRef.current) / 1000);
    const hours = Math.floor(elapsed / 3600).toString().padStart(2, "0");
    const minutes = Math.floor((elapsed % 3600) / 60).toString().padStart(2, "0");
    const seconds = (elapsed % 60).toString().padStart(2, "0");
    setSystemUptime(`${hours}:${minutes}:${seconds}`);
  }, 1000);
  return () => clearInterval(interval);
}, []);

// Fetch real system stats from backend
useEffect(() => {
  async function fetchSystemStats() {
    try {
      const [sysRes, healthRes] = await Promise.all([
        fetch('/api/backend/system-stats').then(r => r.ok ? r.json() : null),
        fetch('/api/backend/health').then(r => r.json()).catch(() => null)
      ]);
      
      if (sysRes) {
        setCpuUsage(sysRes.cpu || 0);
        setMemoryUsage(sysRes.memory || 0);
      }
      if (healthRes?.version) {
        setSystemVersion(healthRes.version);
      }
    } catch (error) {
      console.error('Failed to fetch system stats:', error);
    }
  }
  
  fetchSystemStats();
  // Refresh every 5 seconds
  const interval = setInterval(fetchSystemStats, 5000);
  return () => clearInterval(interval);
}, []);

// Toast helper
const showToast = (message: string) => {
  setToast(message);
  setTimeout(() => setToast(null), 3000);
};

// Handler to toggle agent enabled state and persist to backend
const handleToggleAgent = async (agentId: string, enabled: boolean) => {
  try {
    const response = await fetch('/api/backend/agents', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agentId, enabled }),
    });
    if (response.ok) {
      setAgentList(agentList.map(a => a.id === agentId ? { ...a, enabled } : a));
      showToast(`Agent ${enabled ? 'enabled' : 'disabled'}`);
    }
  } catch (error) {
    console.error('Failed to save agent:', error);
    showToast('Failed to save agent changes');
  }
};

// Handler to toggle MCP connection and persist to backend
const handleToggleMCP = async (mcpId: string, enabled: boolean) => {
  try {
    const response = await fetch('/api/backend/mcp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mcpName: mcpId, enabled }),
    });
    if (response.ok) {
      setMcpList(mcpList.map(m => m.id === mcpId ? { ...m, status: enabled ? 'connected' : 'disconnected' } : m));
      showToast(`MCP ${enabled ? 'enabled' : 'disabled'}`);
    }
  } catch (error) {
    console.error('Failed to save MCP:', error);
    showToast('Failed to save MCP changes');
  }
};

  const tabs = [
    { id: "system", label: "System", icon: Cpu },
    { id: "account", label: "Account", icon: User },
    { id: "notifications", label: "Notifications", icon: Bell },
    { id: "shortcuts", label: "Shortcuts", icon: Keyboard },
    { id: "agents", label: "Agents", icon: Brain },
    { id: "mcp", label: "MCP Connections", icon: Network },
    { id: "routing", label: "Routing", icon: Zap },
    { id: "memory", label: "Memory", icon: Database },
    { id: "developer", label: "Developer", icon: Code2 },
    { id: "api", label: "API & Keys", icon: Key },
    { id: "apikeys", label: "API Keys", icon: Key },
    { id: "appearance", label: "Appearance", icon: Palette },
    { id: "about", label: "About", icon: Info },
  ];

  const StatusIcon = ({ status }: { status: string }) => {
    switch (status) {
      case "connected":
      case "working":
      case "idle":
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case "error":
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return <AlertCircle className="w-4 h-4 text-yellow-500" />;
    }
  };

  return (
    <div className="container mx-auto py-8">
      <div className="flex items-center gap-3 mb-8">
        <Settings className="w-8 h-8" />
        <div>
          <h1 className="text-3xl font-bold">Settings</h1>
          <p className="text-muted-foreground">Configure your N-Xyme MIND workspace</p>
        </div>
      </div>

      <div className="flex gap-6">
        {/* Sidebar */}
        <div className="w-56 shrink-0">
          <nav className="flex flex-col gap-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-3 px-4 py-2.5 rounded-lg text-left transition-colors ${
                  activeTab === tab.id
                    ? "bg-primary text-primary-foreground"
                    : "hover:bg-muted"
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 max-w-3xl">
          {/* Toast notification */}
          {toast && (
            <div className="fixed top-4 right-4 bg-primary text-primary-foreground px-4 py-2 rounded-lg shadow-lg z-50 animate-fade-in">
              {toast}
            </div>
          )}

          {activeTab === "system" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-semibold mb-4">System Status</h2>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 rounded-lg border bg-card">
                    <div className="text-sm text-muted-foreground">Version</div>
                    <div className="text-2xl font-bold">{systemVersion}</div>
                    <div className="text-xs text-muted-foreground">current release</div>
                  </div>
                  <div className="p-4 rounded-lg border bg-card">
                    <div className="text-sm text-muted-foreground">Uptime</div>
                    <div className="text-2xl font-bold">{systemUptime}</div>
                    <div className="text-xs text-muted-foreground">since page load</div>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Resource Usage</h3>
                <div className="p-4 rounded-lg border bg-card space-y-4">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span>CPU Usage</span>
                      <span className="text-muted-foreground">{cpuUsage}%</span>
                    </div>
                    <div className="w-full bg-muted rounded-full h-2">
                      <div 
                        className="bg-blue-500 h-2 rounded-full transition-all" 
                        style={{ width: `${cpuUsage}%` }}
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span>Memory Usage</span>
                      <span className="text-muted-foreground">{memoryUsage}%</span>
                    </div>
                    <div className="w-full bg-muted rounded-full h-2">
                      <div 
                        className="bg-purple-500 h-2 rounded-full transition-all" 
                        style={{ width: `${memoryUsage}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Actions</h3>
                <button 
                  onClick={() => showToast("Services restarting...")}
                  className="w-full flex items-center justify-center gap-2 p-3 rounded-lg border bg-card hover:bg-muted transition-colors"
                >
                  <RefreshCw className="w-5 h-5" />
                  <span>Restart Services</span>
                </button>
              </div>

              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Backup & Restore</h3>
                <div className="flex gap-3">
                  <button 
                    onClick={() => {
                      const today = new Date().toISOString().split('T')[0];
                      const settingsData = {
                        autoRoute,
                        memoryEnabled,
                        developerMode,
                        verboseLogging,
                        selectedTheme,
                        profileName,
                        profileEmail,
                        avatarUrl,
                        desktopNotifications,
                        emailNotifications,
                        soundNotifications,
                        notificationFrequency,
                        shortcuts,
                        selectedFont,
                        accentColor,
                        compactMode,
                        animationsEnabled,
                      };
                      const blob = new Blob([JSON.stringify(settingsData, null, 2)], { type: "application/json" });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement("a");
                      a.href = url;
                      a.download = `nxyme-settings-${today}.json`;
                      a.click();
                      URL.revokeObjectURL(url);
                      showToast("Settings backed up successfully");
                    }}
                    className="flex-1 flex items-center justify-center gap-2 p-3 rounded-lg border bg-card hover:bg-muted transition-colors"
                  >
                    <Download className="w-5 h-5" />
                    <span>Backup Settings</span>
                  </button>
                  <label className="flex-1 flex items-center justify-center gap-2 p-3 rounded-lg border bg-card hover:bg-muted transition-colors cursor-pointer">
                    <Upload className="w-5 h-5" />
                    <span>Restore Settings</span>
                    <input 
                      type="file" 
                      accept=".json"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) {
                          const reader = new FileReader();
                          reader.onload = (ev) => {
                            try {
                              const data = JSON.parse(ev.target?.result as string);
                              // Restore all settings
                              if (data.autoRoute !== undefined) setAutoRoute(data.autoRoute);
                              if (data.memoryEnabled !== undefined) setMemoryEnabled(data.memoryEnabled);
                              if (data.developerMode !== undefined) setDeveloperMode(data.developerMode);
                              if (data.verboseLogging !== undefined) setVerboseLogging(data.verboseLogging);
                              if (data.selectedTheme !== undefined) setSelectedTheme(data.selectedTheme);
                              if (data.profileName !== undefined) setProfileName(data.profileName);
                              if (data.profileEmail !== undefined) setProfileEmail(data.profileEmail);
                              if (data.avatarUrl !== undefined) setAvatarUrl(data.avatarUrl);
                              if (data.desktopNotifications !== undefined) setDesktopNotifications(data.desktopNotifications);
                              if (data.emailNotifications !== undefined) setEmailNotifications(data.emailNotifications);
                              if (data.soundNotifications !== undefined) setSoundNotifications(data.soundNotifications);
                              if (data.notificationFrequency !== undefined) setNotificationFrequency(data.notificationFrequency);
                              if (data.shortcuts !== undefined) setShortcuts(data.shortcuts);
                              if (data.selectedFont !== undefined) setSelectedFont(data.selectedFont);
                              if (data.accentColor !== undefined) setAccentColor(data.accentColor);
                              if (data.compactMode !== undefined) setCompactMode(data.compactMode);
                              if (data.animationsEnabled !== undefined) setAnimationsEnabled(data.animationsEnabled);
                              showToast("Settings restored successfully");
                            } catch {
                              showToast("Invalid backup file");
                            }
                          };
                          reader.readAsText(file);
                        }
                      }}
                    />
                  </label>
                </div>
              </div>
            </div>
          )}

          {activeTab === "agents" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-semibold mb-4">Agent Configuration</h2>
                <div className="space-y-3">
                  {agentList.map((agent) => (
                    <div key={agent.id} className="flex items-center justify-between p-4 rounded-lg border bg-card">
                      <div className="flex items-center gap-3">
                        <Brain className="w-5 h-5 text-muted-foreground" />
                        <div>
                          <div className="font-medium">{agent.name}</div>
                          <div className="text-xs text-muted-foreground">{agent.role}</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <StatusIcon status={agent.enabled ? "connected" : "error"} />
                        <button
                          onClick={() => handleToggleAgent(agent.id, !agent.enabled)}
                          className={`w-12 h-6 rounded-full transition-colors ${agent.enabled ? "bg-primary" : "bg-muted"}`}
                        >
                          <div className={`w-5 h-5 rounded-full bg-white transition-transform ${agent.enabled ? "translate-x-6" : "translate-x-0.5"}`} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
                <button
                  onClick={() => setShowAddAgentForm(true)}
                  className="mt-4 flex items-center gap-2 px-4 py-2 rounded bg-primary text-primary-foreground hover:bg-primary/90"
                >
                  <Plus className="w-4 h-4" />
                  Add Agent
                </button>
              </div>

              {/* Add Agent Form Modal */}
              {showAddAgentForm && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                  <div className="bg-background p-6 rounded-lg border max-w-md w-full">
                    <h3 className="text-lg font-semibold mb-4">Add Agent</h3>
                    <div className="space-y-4">
                      <div>
                        <label className="text-sm text-muted-foreground block mb-1">Name</label>
                        <input
                          type="text"
                          value={newAgentName}
                          onChange={(e) => setNewAgentName(e.target.value)}
                          placeholder="Agent name"
                          className="w-full p-2 rounded border bg-background"
                        />
                      </div>
                      <div>
                        <label className="text-sm text-muted-foreground block mb-1">Role</label>
                        <input
                          type="text"
                          value={newAgentRole}
                          onChange={(e) => setNewAgentRole(e.target.value)}
                          placeholder="e.g., Code Review, Implementation"
                          className="w-full p-2 rounded border bg-background"
                        />
                      </div>
                      <div>
                        <label className="text-sm text-muted-foreground block mb-1">Model</label>
                        <select
                          value={newAgentModel}
                          onChange={(e) => setNewAgentModel(e.target.value)}
                          className="w-full p-2 rounded border bg-background"
                        >
                          <option value="">Select model</option>
                          <option value="minimax-m2.5-free">Minimax M2.5 Free</option>
                          <option value="qwen3.6-plus-free">Qwen 3.6 Plus Free</option>
                          <option value="kimi-k2.5-free">Kimi K2.5 Free</option>
                        </select>
                      </div>
                    </div>
                    <div className="flex gap-3 justify-end mt-6">
                      <button
                        onClick={() => { setShowAddAgentForm(false); setNewAgentName(""); setNewAgentRole(""); setNewAgentModel(""); }}
                        className="px-4 py-2 rounded bg-muted hover:bg-muted/80"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={async () => {
                          if (!newAgentName || !newAgentRole) { showToast("Please fill in name and role"); return; }
                          try {
                            const response = await fetch('/api/backend/agents', {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({ name: newAgentName, role: newAgentRole, model: newAgentModel }),
                            });
                            if (response.ok) {
                              setAgentList([...agentList, { id: Date.now().toString(), name: newAgentName, role: newAgentRole, enabled: true }]);
                              showToast('Agent added successfully');
                            }
                          } catch (error) {
                            console.error('Failed to add agent:', error);
                            showToast('Failed to add agent');
                          }
                          setShowAddAgentForm(false);
                          setNewAgentName(""); setNewAgentRole(""); setNewAgentModel("");
                        }}
                        className="px-4 py-2 rounded bg-primary text-primary-foreground hover:bg-primary/90"
                      >
                        Add Agent
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === "mcp" && (
              <div className="space-y-6">
              <div>
                <h2 className="text-xl font-semibold mb-4">MCP Connections</h2>
                <div className="space-y-3">
                  {mcpList.map((conn) => (
                    <div key={conn.id} className="flex items-center justify-between p-4 rounded-lg border bg-card">
                      <div className="flex items-center gap-3">
                        <Network className="w-5 h-5 text-muted-foreground" />
                        <div>
                          <div className="font-medium">{conn.name}</div>
                          <div className="text-xs text-muted-foreground">{conn.type}</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <StatusIcon status={conn.status} />
                        <button
                          onClick={() => handleToggleMCP(conn.id, conn.status !== 'connected')}
                          className={`w-12 h-6 rounded-full transition-colors ${conn.status === 'connected' ? "bg-primary" : "bg-muted"}`}
                        >
                          <div className={`w-5 h-5 rounded-full bg-white transition-transform ${conn.status === 'connected' ? "translate-x-6" : "translate-x-0.5"}`} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
                <button
                  onClick={() => setShowAddMcpForm(true)}
                  className="mt-4 flex items-center gap-2 px-4 py-2 rounded bg-primary text-primary-foreground hover:bg-primary/90"
                >
                  <Plus className="w-4 h-4" />
                  Add MCP
                </button>
              </div>

              {/* Add MCP Form Modal */}
              {showAddMcpForm && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                  <div className="bg-background p-6 rounded-lg border max-w-md w-full">
                    <h3 className="text-lg font-semibold mb-4">Add MCP Connection</h3>
                    <div className="space-y-4">
                      <div>
                        <label className="text-sm text-muted-foreground block mb-1">Name</label>
                        <input
                          type="text"
                          value={newMcpName}
                          onChange={(e) => setNewMcpName(e.target.value)}
                          placeholder="Connection name"
                          className="w-full p-2 rounded border bg-background"
                        />
                      </div>
                      <div>
                        <label className="text-sm text-muted-foreground block mb-1">Type</label>
                        <select
                          value={newMcpType}
                          onChange={(e) => setNewMcpType(e.target.value)}
                          className="w-full p-2 rounded border bg-background"
                        >
                          <option value="">Select type</option>
                          <option value="filesystem">Filesystem</option>
                          <option value="git">Git</option>
                          <option value="github">GitHub</option>
                          <option value="memory">Memory</option>
                          <option value="sequential-thinking">Sequential Thinking</option>
                          <option value="context7">Context7</option>
                        </select>
                      </div>
                    </div>
                    <div className="flex gap-3 justify-end mt-6">
                      <button
                        onClick={() => { setShowAddMcpForm(false); setNewMcpName(""); setNewMcpType(""); }}
                        className="px-4 py-2 rounded bg-muted hover:bg-muted/80"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={async () => {
                          if (!newMcpName || !newMcpType) { showToast("Please fill in all fields"); return; }
                          try {
                            const response = await fetch('/api/backend/mcp', {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({ name: newMcpName, type: newMcpType }),
                            });
                            if (response.ok) {
                              setMcpList([...mcpList, { id: Date.now().toString(), name: newMcpName, type: newMcpType, status: "connected" }]);
                              showToast('MCP connection added successfully');
                            }
                          } catch (error) {
                            console.error('Failed to add MCP:', error);
                            showToast('Failed to add MCP connection');
                          }
                          setShowAddMcpForm(false);
                          setNewMcpName(""); setNewMcpType("");
                        }}
                        className="px-4 py-2 rounded bg-primary text-primary-foreground hover:bg-primary/90"
                      >
                        Add MCP
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === "routing" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-semibold mb-4">Smart Routing</h2>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 rounded-lg border bg-card">
                    <div>
                      <div className="font-medium">Auto-Route Tasks</div>
                      <div className="text-sm text-muted-foreground">Automatically route tasks to optimal agents</div>
                    </div>
                    <button
                      onClick={() => setAutoRoute(!autoRoute)}
                      className={`w-12 h-6 rounded-full transition-colors ${
                        autoRoute ? "bg-primary" : "bg-muted"
                      }`}
                    >
                      <div className={`w-5 h-5 rounded-full bg-white transition-transform ${
                        autoRoute ? "translate-x-6" : "translate-x-0.5"
                      }`} />
                    </button>
                  </div>

                  <div className="p-4 rounded-lg border bg-card">
                    <div className="font-medium mb-3">Provider Priority Order</div>
                    <div className="space-y-2">
                      {providerPriority.map((provider, idx) => (
                        <div key={provider.id} className="flex items-center justify-between p-2 rounded bg-muted/50">
                          <div className="flex items-center gap-3">
                            <span className="text-sm text-muted-foreground w-6">{idx + 1}.</span>
                            <span className="font-medium">{provider.name}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => {
                                if (idx > 0) {
                                  const newPriority = [...providerPriority];
                                  [newPriority[idx - 1], newPriority[idx]] = [newPriority[idx], newPriority[idx - 1]];
                                  setProviderPriority(newPriority);
                                }
                              }}
                              disabled={idx === 0}
                              className="p-1 rounded hover:bg-muted disabled:opacity-50"
                            >
                              ↑
                            </button>
                            <button
                              onClick={() => {
                                if (idx < providerPriority.length - 1) {
                                  const newPriority = [...providerPriority];
                                  [newPriority[idx], newPriority[idx + 1]] = [newPriority[idx + 1], newPriority[idx]];
                                  setProviderPriority(newPriority);
                                }
                              }}
                              disabled={idx === providerPriority.length - 1}
                              className="p-1 rounded hover:bg-muted disabled:opacity-50"
                            >
                              ↓
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center justify-between p-4 rounded-lg border bg-card">
                    <div>
                      <div className="font-medium">Fallback Enabled</div>
                      <div className="text-sm text-muted-foreground">Use next provider if primary fails</div>
                    </div>
                    <button
                      onClick={() => setFallbackEnabled(!fallbackEnabled)}
                      className={`w-12 h-6 rounded-full transition-colors ${
                        fallbackEnabled ? "bg-primary" : "bg-muted"
                      }`}
                    >
                      <div className={`w-5 h-5 rounded-full bg-white transition-transform ${
                        fallbackEnabled ? "translate-x-6" : "translate-x-0.5"
                      }`} />
                    </button>
                  </div>

                  <div className="p-4 rounded-lg border bg-card">
                    <div className="font-medium mb-2">Monthly Cost Limit</div>
                    <div className="text-sm text-muted-foreground mb-2">Stop routing when limit is reached</div>
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground">$</span>
                      <input
                        type="number"
                        value={costLimit}
                        onChange={(e) => setCostLimit(Number(e.target.value))}
                        className="w-24 p-2 rounded border bg-background"
                        min={1}
                        max={1000}
                      />
                      <span className="text-muted-foreground">/ month</span>
                    </div>
                  </div>

                  <div className="p-4 rounded-lg border bg-card">
                    <div className="font-medium mb-3">AI Provider</div>
                    <div className="grid grid-cols-3 gap-2">
                      {["opencode", "anthropic", "openai"].map((provider) => (
                        <button
                          key={provider}
                          onClick={() => setAiProvider(provider)}
                          className={`p-3 rounded-lg border text-sm capitalize ${
                            aiProvider === provider
                              ? "border-primary bg-primary/10"
                              : "hover:bg-muted"
                          }`}
                        >
                          {provider}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "memory" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-semibold mb-4">Memory System</h2>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 rounded-lg border bg-card">
                    <div>
                      <div className="font-medium">Enable Memory</div>
                      <div className="text-sm text-muted-foreground">Store semantic and episodic memories</div>
                    </div>
                    <button
                      onClick={() => setMemoryEnabled(!memoryEnabled)}
                      className={`w-12 h-6 rounded-full transition-colors ${
                        memoryEnabled ? "bg-primary" : "bg-muted"
                      }`}
                    >
                      <div className={`w-5 h-5 rounded-full bg-white transition-transform ${
                        memoryEnabled ? "translate-x-6" : "translate-x-0.5"
                      }`} />
                    </button>
                  </div>

                  <div className="p-4 rounded-lg border bg-card">
                    <div className="font-medium mb-3">Memory Retention Period</div>
                    <select 
                      value={memoryRetention}
                      onChange={(e) => setMemoryRetention(e.target.value)}
                      className="w-full p-2 rounded border bg-background"
                    >
                      <option value="7">7 days</option>
                      <option value="30">30 days</option>
                      <option value="90">90 days</option>
                      <option value="forever">Forever</option>
                    </select>
                  </div>

                  <div className="flex items-center justify-between p-4 rounded-lg border bg-card">
                    <div>
                      <div className="font-medium">Auto-Cleanup</div>
                      <div className="text-sm text-muted-foreground">Automatically remove old memories</div>
                    </div>
                    <button
                      onClick={() => setAutoCleanup(!autoCleanup)}
                      className={`w-12 h-6 rounded-full transition-colors ${
                        autoCleanup ? "bg-primary" : "bg-muted"
                      }`}
                    >
                      <div className={`w-5 h-5 rounded-full bg-white transition-transform ${
                        autoCleanup ? "translate-x-6" : "translate-x-0.5"
                      }`} />
                    </button>
                  </div>

                  <div className="flex items-center justify-between p-4 rounded-lg border bg-card">
                    <div>
                      <div className="font-medium">Memory Compression</div>
                      <div className="text-sm text-muted-foreground">Reduce memory footprint with compression</div>
                    </div>
                    <button
                      onClick={() => setMemoryCompression(!memoryCompression)}
                      className={`w-12 h-6 rounded-full transition-colors ${
                        memoryCompression ? "bg-primary" : "bg-muted"
                      }`}
                    >
                      <div className={`w-5 h-5 rounded-full bg-white transition-transform ${
                        memoryCompression ? "translate-x-6" : "translate-x-0.5"
                      }`} />
                    </button>
                  </div>

                  <div className="p-4 rounded-lg border bg-card">
                    <div className="text-sm text-muted-foreground mb-2">Memory Sources</div>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between py-2">
                        <span>Sequential Thinking</span>
                        <CheckCircle className="w-4 h-4 text-green-500" />
                      </div>
                      <div className="flex items-center justify-between py-2">
                        <span>Unified Memory</span>
                        <CheckCircle className="w-4 h-4 text-green-500" />
                      </div>
                      <div className="flex items-center justify-between py-2">
                        <span>Context7</span>
                        <CheckCircle className="w-4 h-4 text-green-500" />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "developer" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-semibold mb-4">Developer Settings</h2>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 rounded-lg border bg-card">
                    <div>
                      <div className="font-medium">Developer Mode</div>
                      <div className="text-sm text-muted-foreground">Enable advanced debugging features</div>
                    </div>
                    <button
                      onClick={() => setDeveloperMode(!developerMode)}
                      className={`w-12 h-6 rounded-full transition-colors ${
                        developerMode ? "bg-primary" : "bg-muted"
                      }`}
                    >
                      <div className={`w-5 h-5 rounded-full bg-white transition-transform ${
                        developerMode ? "translate-x-6" : "translate-x-0.5"
                      }`} />
                    </button>
                  </div>

                  <div className="flex items-center justify-between p-4 rounded-lg border bg-card">
                    <div>
                      <div className="font-medium">Verbose Logging</div>
                      <div className="text-sm text-muted-foreground">Log all agent actions and decisions</div>
                    </div>
                    <button
                      onClick={() => setVerboseLogging(!verboseLogging)}
                      className={`w-12 h-6 rounded-full transition-colors ${
                        verboseLogging ? "bg-primary" : "bg-muted"
                      }`}
                    >
                      <div className={`w-5 h-5 rounded-full bg-white transition-transform ${
                        verboseLogging ? "translate-x-6" : "translate-x-0.5"
                      }`} />
                    </button>
                  </div>

                  {developerMode && (
                    <div className="space-y-3">
                      <div className="p-4 rounded-lg border bg-card">
                        <div className="flex items-center gap-2 mb-3">
                          <Terminal className="w-4 h-4" />
                          <span className="font-medium">Developer Tools</span>
                        </div>
                        <div className="space-y-2">
                          <button 
                            onClick={() => runDevTool("View Agent State")}
                            className="w-full text-left p-2 rounded hover:bg-muted text-sm"
                          >
                            View Agent State
                          </button>
                          <button 
                            onClick={() => runDevTool("Inspect Task Queue")}
                            className="w-full text-left p-2 rounded hover:bg-muted text-sm"
                          >
                            Inspect Task Queue
                          </button>
                          <button 
                            onClick={() => runDevTool("MCP Inspector")}
                            className="w-full text-left p-2 rounded hover:bg-muted text-sm"
                          >
                            MCP Inspector
                          </button>
                          <button 
                            onClick={() => runDevTool("Session History")}
                            className="w-full text-left p-2 rounded hover:bg-muted text-sm"
                          >
                            Session History
                          </button>
                          <button 
                            onClick={() => runDevTool("Routing Debugger")}
                            className="w-full text-left p-2 rounded hover:bg-muted text-sm"
                          >
                            Routing Debugger
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === "api" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-semibold mb-4">API & Keys</h2>
                <div className="space-y-4">
                  <div className="p-4 rounded-lg border bg-card">
                    <div className="flex items-center gap-2 mb-3">
                      <Globe className="w-4 h-4" />
                      <span className="font-medium">OpenCode</span>
                    </div>
                    <div className="text-sm text-muted-foreground mb-2">Status: Connected</div>
                    <input 
                      type="password" 
                      value="••••••••••••••••" 
                      readOnly
                      className="w-full p-2 rounded bg-muted text-sm"
                    />
                  </div>

                  <div className="p-4 rounded-lg border bg-card">
                    <div className="flex items-center gap-2 mb-3">
                      <Shield className="w-4 h-4" />
                      <span className="font-medium">SOCKS5 Proxies</span>
                    </div>
                    <div className="text-sm text-muted-foreground mb-2">8 proxies configured (ports 1080-1087)</div>
                    <button className="px-4 py-2 rounded bg-muted hover:bg-muted/80 text-sm">
                      Configure Proxies
                    </button>
                  </div>

                  <div className="p-4 rounded-lg border bg-card">
                    <div className="flex items-center gap-2 mb-3">
                      <Key className="w-4 h-4" />
                      <span className="font-medium">GitHub Token</span>
                    </div>
                    <div className="text-sm text-muted-foreground mb-2">Status: Not configured</div>
                    <button className="px-4 py-2 rounded bg-muted hover:bg-muted/80 text-sm">
                      Add Token
                    </button>
                  </div>

                  <div className="p-4 rounded-lg border bg-card">
                    <div className="flex items-center gap-2 mb-3">
                      <Download className="w-4 h-4" />
                      <span className="font-medium">Data Management</span>
                    </div>
                    <div className="space-y-2">
                      <button 
                        onClick={() => {
                          const settings = localStorage.getItem("settings") || "{}";
                          const blob = new Blob([settings], { type: "application/json" });
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement("a");
                          a.href = url;
                          a.download = "nxyme-mind-settings.json";
                          a.click();
                          URL.revokeObjectURL(url);
                        }}
                        className="w-full flex items-center justify-between p-2 rounded hover:bg-muted text-sm"
                      >
                        <span className="flex items-center gap-2">
                          <Download className="w-4 h-4" />
                          Export Settings
                        </span>
                      </button>
                      <label className="w-full flex items-center justify-between p-2 rounded hover:bg-muted text-sm cursor-pointer">
                        <span className="flex items-center gap-2">
                          <ImportIcon className="w-4 h-4" />
                          Import Settings
                        </span>
                        <input 
                          type="file" 
                          accept=".json"
                          className="hidden"
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) {
                              const reader = new FileReader();
                              reader.onload = (ev) => {
                                try {
                                  const data = JSON.parse(ev.target?.result as string);
                                  localStorage.setItem("settings", JSON.stringify(data));
                                  showToast("Settings imported successfully! Please refresh the page.");
                                  window.location.reload();
                                } catch {
                                  showToast("Invalid settings file.");
                                }
                              };
                              reader.readAsText(file);
                            }
                          }}
                        />
                      </label>
                      <button 
                        onClick={() => {
                          setConfirmMessage("Are you sure you want to clear all data? This action cannot be undone.");
                          setConfirmAction(() => () => {
                            localStorage.clear();
                            showToast("All data cleared. Please refresh the page.");
                            window.location.reload();
                          });
                          setShowConfirmDialog(true);
                        }}
                        className="w-full flex items-center justify-between p-2 rounded hover:bg-muted text-sm text-red-500"
                      >
                        <span className="flex items-center gap-2">
                          <Trash2 className="w-4 h-4" />
                          Clear All Data
                        </span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "apikeys" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-semibold mb-4">API Keys</h2>
                <p className="text-sm text-muted-foreground mb-4">
                  Manage your API keys for external services.
                </p>
                
                <div className="space-y-3">
                  {apiKeys.map((apiKey) => (
                    <div key={apiKey.id} className="p-4 rounded-lg border bg-card space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Key className="w-5 h-5 text-muted-foreground" />
                          <div>
                            <div className="font-medium flex items-center gap-2">
                              {apiKey.name}
                              <span className={`text-xs px-2 py-0.5 rounded-full ${
                                apiKey.permission === "full-access" 
                                  ? "bg-orange-500/20 text-orange-400" 
                                  : "bg-blue-500/20 text-blue-400"
                              }`}>
                                {apiKey.permission === "full-access" ? "Full Access" : "Read-only"}
                              </span>
                            </div>
                            <div className="text-xs text-muted-foreground">
                              {apiKey.provider} • Added {apiKey.createdAt}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <code className="text-sm bg-muted px-2 py-1 rounded">
                            {visibleKeys.has(apiKey.id) ? apiKey.key : "••••••••••••••••"}
                          </code>
                          <button
                            onClick={() => {
                              const newVisible = new Set(visibleKeys);
                              if (newVisible.has(apiKey.id)) {
                                newVisible.delete(apiKey.id);
                              } else {
                                newVisible.add(apiKey.id);
                              }
                              setVisibleKeys(newVisible);
                            }}
                            className="p-2 rounded hover:bg-muted"
                            title={visibleKeys.has(apiKey.id) ? "Hide" : "Show"}
                          >
                            {visibleKeys.has(apiKey.id) ? (
                              <EyeOff className="w-4 h-4" />
                            ) : (
                              <Eye className="w-4 h-4" />
                            )}
                          </button>
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(apiKey.key);
                              showToast("Key copied to clipboard!");
                            }}
                            className="p-2 rounded hover:bg-muted"
                            title="Copy"
                          >
                            <Copy className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => {
                              setConfirmMessage(`Are you sure you want to delete the ${apiKey.name} API key?`);
                              setConfirmAction(() => () => {
                                setApiKeys(apiKeys.filter(k => k.id !== apiKey.id));
                              });
                              setShowConfirmDialog(true);
                            }}
                            className="p-2 rounded hover:bg-muted text-red-500"
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                      
                      {/* Permissions dropdown */}
                      <div className="flex items-center gap-2 pt-2 border-t">
                        <span className="text-xs text-muted-foreground">Permission:</span>
                        <select
                          value={apiKey.permission}
                          onChange={(e) => {
                            setApiKeys(apiKeys.map(k => 
                              k.id === apiKey.id 
                                ? { ...k, permission: e.target.value as "read-only" | "full-access" } 
                                : k
                            ));
                          }}
                          className="text-xs p-1 rounded border bg-background"
                        >
                          <option value="read-only">Read-only</option>
                          <option value="full-access">Full Access</option>
                        </select>
                      </div>
                      
                      {/* Usage section */}
                      {apiKey.usage && (
                        <div className="pt-2 border-t">
                          <div className="text-xs text-muted-foreground mb-2">Usage this month</div>
                          <div className="grid grid-cols-3 gap-2 text-xs">
                            <div className="bg-muted/50 p-2 rounded">
                              <div className="text-muted-foreground">API Calls</div>
                              <div className="font-medium">{apiKey.usage.callsThisMonth.toLocaleString()}</div>
                            </div>
                            <div className="bg-muted/50 p-2 rounded">
                              <div className="text-muted-foreground">Tokens</div>
                              <div className="font-medium">{apiKey.usage.tokensUsed.toLocaleString()}</div>
                            </div>
                            <div className="bg-muted/50 p-2 rounded">
                              <div className="text-muted-foreground">Last Used</div>
                              <div className="font-medium">{apiKey.usage.lastUsed}</div>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {apiKeys.length === 0 && (
                  <div className="text-center p-8 text-muted-foreground">
                    No API keys configured. Add your first key below.
                  </div>
                )}

                <button
                  onClick={() => setShowAddKeyModal(true)}
                  className="mt-4 flex items-center gap-2 px-4 py-2 rounded bg-primary text-primary-foreground hover:bg-primary/90"
                >
                  <Plus className="w-4 h-4" />
                  Add API Key
                </button>
              </div>

              {/* Add Key Modal */}
              {showAddKeyModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                  <div className="bg-background p-6 rounded-lg border max-w-md w-full">
                    <h3 className="text-lg font-semibold mb-4">Add API Key</h3>
                    <div className="space-y-4">
                      <div>
                        <label className="text-sm text-muted-foreground block mb-1">Name</label>
                        <input
                          type="text"
                          value={newKeyName}
                          onChange={(e) => setNewKeyName(e.target.value)}
                          placeholder="My API Key"
                          className="w-full p-2 rounded border bg-background"
                        />
                      </div>
                      <div>
                        <label className="text-sm text-muted-foreground block mb-1">Provider</label>
                        <select
                          value={newKeyProvider}
                          onChange={(e) => setNewKeyProvider(e.target.value)}
                          className="w-full p-2 rounded border bg-background"
                        >
                          <option value="">Select provider</option>
                          <option value="OpenAI">OpenAI</option>
                          <option value="Anthropic">Anthropic</option>
                          <option value="GitHub">GitHub</option>
                          <option value="Google">Google</option>
                          <option value="AWS">AWS</option>
                          <option value="Azure">Azure</option>
                          <option value="Other">Other</option>
                        </select>
                      </div>
                      <div>
                        <label className="text-sm text-muted-foreground block mb-1">Permission</label>
                        <select
                          value={newKeyPermission}
                          onChange={(e) => setNewKeyPermission(e.target.value as "read-only" | "full-access")}
                          className="w-full p-2 rounded border bg-background"
                        >
                          <option value="read-only">Read-only</option>
                          <option value="full-access">Full Access</option>
                        </select>
                      </div>
                      <div>
                        <label className="text-sm text-muted-foreground block mb-1">API Key</label>
                        <input
                          type="password"
                          value={newKeyValue}
                          onChange={(e) => setNewKeyValue(e.target.value)}
                          placeholder="sk-..."
                          className="w-full p-2 rounded border bg-background"
                        />
                      </div>
                    </div>
                    <div className="flex gap-3 justify-end mt-6">
                      <button
                        onClick={() => {
                          setShowAddKeyModal(false);
                          setNewKeyName("");
                          setNewKeyValue("");
                          setNewKeyProvider("");
                          setNewKeyPermission("full-access");
                        }}
                        className="px-4 py-2 rounded bg-muted hover:bg-muted/80"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => {
                          if (!newKeyName || !newKeyValue || !newKeyProvider) {
                            showToast("Please fill in all fields");
                            return;
                          }
                          const newKey: ApiKey = {
                            id: Date.now().toString(),
                            name: newKeyName,
                            key: newKeyValue,
                            provider: newKeyProvider,
                            createdAt: new Date().toISOString().split("T")[0],
                            permission: newKeyPermission,
                            usage: { callsThisMonth: 0, tokensUsed: 0, lastUsed: "-" },
                          };
                          setApiKeys([...apiKeys, newKey]);
                          setShowAddKeyModal(false);
                          setNewKeyName("");
                          setNewKeyValue("");
                          setNewKeyProvider("");
                        }}
                        className="px-4 py-2 rounded bg-primary text-primary-foreground hover:bg-primary/90"
                      >
                        Add Key
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === "appearance" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-semibold mb-4">Appearance</h2>
                <div className="space-y-4">
                  <div className="p-4 rounded-lg border bg-card">
                    <div className="font-medium mb-3">Theme</div>
                    <div className="grid grid-cols-3 gap-2">
                      <button 
                        onClick={() => { setSelectedTheme("dark"); showToast("Theme set to Dark"); }}
                        className={`p-3 rounded-lg border text-center ${selectedTheme === "dark" ? "border-primary bg-primary/10" : "hover:bg-muted"}`}
                      >
                        <div className="text-2xl mb-1">🌙</div>
                        <div className="text-sm">Dark</div>
                      </button>
                      <button 
                        onClick={() => { setSelectedTheme("light"); showToast("Theme set to Light"); }}
                        className={`p-3 rounded-lg border text-center ${selectedTheme === "light" ? "border-primary bg-primary/10" : "hover:bg-muted"}`}
                      >
                        <div className="text-2xl mb-1">☀️</div>
                        <div className="text-sm">Light</div>
                      </button>
                      <button 
                        onClick={() => { setSelectedTheme("system"); showToast("Theme set to System"); }}
                        className={`p-3 rounded-lg border text-center ${selectedTheme === "system" ? "border-primary bg-primary/10" : "hover:bg-muted"}`}
                      >
                        <div className="text-2xl mb-1">🖥️</div>
                        <div className="text-sm">System</div>
                      </button>
                    </div>
                  </div>

                  <div className="p-4 rounded-lg border bg-card">
                    <div className="font-medium mb-3">Font</div>
                    <select 
                      value={selectedFont}
                      onChange={(e) => { setSelectedFont(e.target.value); showToast(`Font set to ${e.target.value}`); }}
                      className="w-full p-2 rounded border bg-background"
                    >
                      <option value="System">System</option>
                      <option value="Inter">Inter</option>
                      <option value="Roboto">Roboto</option>
                      <option value="Mono">Mono</option>
                    </select>
                  </div>

                  <div className="p-4 rounded-lg border bg-card">
                    <div className="font-medium mb-3">Accent Color</div>
                    <div className="flex gap-2">
                      {[
                        { id: "blue", color: "#3b82f6" },
                        { id: "purple", color: "#8b5cf6" },
                        { id: "pink", color: "#ec4899" },
                        { id: "red", color: "#ef4444" },
                        { id: "orange", color: "#f97316" },
                        { id: "green", color: "#22c55e" },
                      ].map((c) => (
                        <button
                          key={c.id}
                          onClick={() => { setAccentColor(c.id); showToast(`Accent color set to ${c.id}`); }}
                          className={`w-10 h-10 rounded-lg border-2 ${accentColor === c.id ? "border-foreground" : "border-transparent"}`}
                          style={{ backgroundColor: c.color }}
                        />
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center justify-between p-4 rounded-lg border bg-card">
                    <div>
                      <div className="font-medium">Compact Mode</div>
                      <div className="text-sm text-muted-foreground">Reduce spacing and padding</div>
                    </div>
                    <button 
                      onClick={() => setCompactMode(!compactMode)}
                      className={`w-12 h-6 rounded-full transition-colors ${compactMode ? "bg-primary" : "bg-muted"}`}
                    >
                      <div className={`w-5 h-5 rounded-full bg-white transition-transform ${compactMode ? "translate-x-6" : "translate-x-0.5"}`} />
                    </button>
                  </div>

                  <div className="flex items-center justify-between p-4 rounded-lg border bg-card">
                    <div>
                      <div className="font-medium">Animations</div>
                      <div className="text-sm text-muted-foreground">Enable UI animations and transitions</div>
                    </div>
                    <button 
                      onClick={() => setAnimationsEnabled(!animationsEnabled)}
                      className={`w-12 h-6 rounded-full transition-colors ${animationsEnabled ? "bg-primary" : "bg-muted"}`}
                    >
                      <div className={`w-5 h-5 rounded-full bg-white transition-transform ${animationsEnabled ? "translate-x-6" : "translate-x-0.5"}`} />
                    </button>
                  </div>

                  <div className="flex items-center justify-between p-4 rounded-lg border bg-card">
                    <div>
                      <div className="font-medium">Notifications</div>
                      <div className="text-sm text-muted-foreground">Show system notifications</div>
                    </div>
                    <button 
                      onClick={() => setDesktopNotifications(!desktopNotifications)}
                      className={`w-12 h-6 rounded-full transition-colors ${desktopNotifications ? "bg-primary" : "bg-muted"}`}
                    >
                      <div className={`w-5 h-5 rounded-full bg-white transition-transform ${desktopNotifications ? "translate-x-6" : "translate-x-0.5"}`} />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Account Section */}
          {activeTab === "account" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-semibold mb-4">Account Settings</h2>
                <div className="space-y-4">
                  <div className="p-6 rounded-lg border bg-card">
                    <div className="flex items-center gap-4 mb-4">
                      <div className="w-20 h-20 rounded-full bg-muted flex items-center justify-center overflow-hidden">
                        {avatarUrl ? (
                          <img src={avatarUrl} alt="Avatar" className="w-full h-full object-cover" />
                        ) : (
                          <User className="w-10 h-10 text-muted-foreground" />
                        )}
                      </div>
                      <div>
                        <label className="cursor-pointer flex items-center gap-2 px-3 py-1.5 rounded bg-muted hover:bg-muted/80 text-sm">
                          <Upload className="w-4 h-4" />
                          Upload Avatar
                          <input 
                            type="file" 
                            accept="image/*"
                            className="hidden"
                            onChange={(e) => {
                              const file = e.target.files?.[0];
                              if (file) {
                                const reader = new FileReader();
                                reader.onload = (ev) => setAvatarUrl(ev.target?.result as string);
                                reader.readAsDataURL(file);
                              }
                            }}
                          />
                        </label>
                      </div>
                    </div>
                    <div className="space-y-3">
                      <div>
                        <label className="text-sm text-muted-foreground block mb-1">Name</label>
                        <input 
                          type="text"
                          value={profileName}
                          onChange={(e) => setProfileName(e.target.value)}
                          placeholder="Enter your name"
                          className="w-full p-2 rounded border bg-background"
                        />
                      </div>
                      <div>
                        <label className="text-sm text-muted-foreground block mb-1">Email</label>
                        <input 
                          type="email"
                          value={profileEmail}
                          onChange={(e) => setProfileEmail(e.target.value)}
                          placeholder="Enter your email"
                          className="w-full p-2 rounded border bg-background"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Notifications Section */}
          {activeTab === "notifications" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-semibold mb-4">Notification Preferences</h2>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 rounded-lg border bg-card">
                    <div>
                      <div className="font-medium">Browser Notifications</div>
                      <div className="text-sm text-muted-foreground">Show notifications in your browser</div>
                    </div>
                    <button 
                      onClick={() => setDesktopNotifications(!desktopNotifications)}
                      className={`w-12 h-6 rounded-full transition-colors ${desktopNotifications ? "bg-primary" : "bg-muted"}`}
                    >
                      <div className={`w-5 h-5 rounded-full bg-white transition-transform ${desktopNotifications ? "translate-x-6" : "translate-x-0.5"}`} />
                    </button>
                  </div>

                  <button 
                    onClick={() => {
                      if ("Notification" in window) {
                        if (Notification.permission === "granted") {
                          new Notification("Test Notification", { body: "N-Xyme MIND is working!" });
                          showToast("Test notification sent!");
                        } else if (Notification.permission !== "denied") {
                          Notification.requestPermission().then((permission) => {
                            if (permission === "granted") {
                              new Notification("Test Notification", { body: "N-Xyme MIND is working!" });
                              showToast("Test notification sent!");
                            } else {
                              showToast("Notification permission denied");
                            }
                          });
                        } else {
                          showToast("Notification permission denied");
                        }
                      } else {
                        showToast("Notifications not supported in this browser");
                      }
                    }}
                    className="w-full flex items-center justify-center gap-2 p-3 rounded-lg border bg-card hover:bg-muted transition-colors"
                  >
                    <Bell className="w-5 h-5" />
                    <span>Test Notification</span>
                  </button>

                  <div className="flex items-center justify-between p-4 rounded-lg border bg-card">
                    <div>
                      <div className="font-medium flex items-center gap-2">
                        <Mail className="w-4 h-4" />
                        Email Notifications
                      </div>
                      <div className="text-sm text-muted-foreground">Receive updates via email</div>
                    </div>
                    <button 
                      onClick={async () => {
                        const newValue = !emailNotifications;
                        try {
                          const response = await fetch('/api/backend/settings', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ settings: { notifications: newValue } }),
                          });
                          if (response.ok) {
                            setEmailNotifications(newValue);
                            showToast(`Email notifications ${newValue ? 'enabled' : 'disabled'}`);
                          } else {
                            showToast('Failed to save email setting');
                          }
                        } catch (error) {
                          console.error('Failed to save email setting:', error);
                          showToast('Failed to save email setting');
                        }
                      }}
                      className={`w-12 h-6 rounded-full transition-colors ${emailNotifications ? "bg-primary" : "bg-muted"}`}
                    >
                      <div className={`w-5 h-5 rounded-full bg-white transition-transform ${emailNotifications ? "translate-x-6" : "translate-x-0.5"}`} />
                    </button>
                  </div>

                  <div className="flex items-center justify-between p-4 rounded-lg border bg-card">
                    <div>
                      <div className="font-medium flex items-center gap-2">
                        <Globe className="w-4 h-4" />
                        Slack Notifications
                      </div>
                      <div className="text-sm text-muted-foreground">Send notifications to Slack</div>
                    </div>
                    <button 
                      onClick={async () => {
                        const newValue = !slackNotifications;
                        try {
                          const response = await fetch('/api/backend/settings', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ settings: { slackNotifications: newValue } }),
                          });
                          if (response.ok) {
                            setSlackNotifications(newValue);
                            showToast(`Slack notifications ${newValue ? 'enabled' : 'disabled'}`);
                          } else {
                            showToast('Failed to save Slack setting');
                          }
                        } catch (error) {
                          console.error('Failed to save Slack setting:', error);
                          showToast('Failed to save Slack setting');
                        }
                      }}
                      className={`w-12 h-6 rounded-full transition-colors ${slackNotifications ? "bg-primary" : "bg-muted"}`}
                    >
                      <div className={`w-5 h-5 rounded-full bg-white transition-transform ${slackNotifications ? "translate-x-6" : "translate-x-0.5"}`} />
                    </button>
                  </div>

                  <div className="flex items-center justify-between p-4 rounded-lg border bg-card">
                    <div>
                      <div className="font-medium flex items-center gap-2">
                        <Volume2 className="w-4 h-4" />
                        Sound Notifications
                      </div>
                      <div className="text-sm text-muted-foreground">Play sound for notifications</div>
                    </div>
                    <button 
                      onClick={() => setSoundNotifications(!soundNotifications)}
                      className={`w-12 h-6 rounded-full transition-colors ${soundNotifications ? "bg-primary" : "bg-muted"}`}
                    >
                      <div className={`w-5 h-5 rounded-full bg-white transition-transform ${soundNotifications ? "translate-x-6" : "translate-x-0.5"}`} />
                    </button>
                  </div>

                  <div className="p-4 rounded-lg border bg-card">
                    <div className="font-medium mb-3">Notification Frequency</div>
                    <select 
                      value={notificationFrequency}
                      onChange={(e) => setNotificationFrequency(e.target.value)}
                      className="w-full p-2 rounded border bg-background"
                    >
                      <option value="instant">Instant</option>
                      <option value="hourly">Hourly Digest</option>
                      <option value="daily">Daily Digest</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Keyboard Shortcuts Section */}
          {activeTab === "shortcuts" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-semibold mb-4">Keyboard Shortcuts</h2>
                <div className="space-y-4">
                  <div className="p-4 rounded-lg border bg-card">
                    <div className="space-y-2">
                      {shortcuts.map((shortcut) => (
                        <div key={shortcut.id} className="flex items-center justify-between py-2">
                          <span>{shortcut.action}</span>
                          {editingShortcut === shortcut.id ? (
                            <div className="flex items-center gap-2">
                              <input 
                                type="text"
                                value={editKey}
                                onChange={(e) => setEditKey(e.target.value)}
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") {
                                    setShortcuts(shortcuts.map(s => s.id === shortcut.id ? { ...s, key: editKey } : s));
                                    setEditingShortcut(null);
                                  } else if (e.key === "Escape") {
                                    setEditingShortcut(null);
                                  }
                                }}
                                className="w-24 p-1 text-center rounded border bg-background text-sm"
                                autoFocus
                              />
                              <button 
                                onClick={() => {
                                  setShortcuts(shortcuts.map(s => s.id === shortcut.id ? { ...s, key: editKey } : s));
                                  setEditingShortcut(null);
                                }}
                                className="text-green-500 text-sm"
                              >
                                Save
                              </button>
                            </div>
                          ) : (
                            <button 
                              onClick={() => { setEditingShortcut(shortcut.id); setEditKey(shortcut.key); }}
                              className="px-2 py-1 rounded bg-muted hover:bg-muted/80 text-sm"
                            >
                              {shortcut.key}
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                  <button 
                    onClick={() => setShortcuts(defaultShortcuts)}
                    className="flex items-center gap-2 px-4 py-2 rounded bg-muted hover:bg-muted/80 text-sm"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Reset to Defaults
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* About Section */}
          {activeTab === "about" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-semibold mb-4">About N-Xyme MIND</h2>
                <div className="space-y-4">
                  <div className="p-4 rounded-lg border bg-card">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
                        <Brain className="w-6 h-6 text-primary" />
                      </div>
                      <div>
                        <div className="font-medium">N-Xyme MIND</div>
                        <div className="text-sm text-muted-foreground">Version 1.0.0</div>
                      </div>
                    </div>
                    <p className="text-sm text-muted-foreground mb-4">
                      Personal AI coding workspace powered by OpenCode + OMO multi-agent orchestration.
                    </p>
                    <button 
                      onClick={async () => {
                        try {
                          const response = await fetch('/api/backend/health', { method: 'GET' });
                          const data = await response.json();
                          if (response.ok && data.version) {
                            showToast(`Current version: ${data.version}\n\nYou are running v${data.version}`);
                          } else {
                            showToast('You are running version 1.0.0');
                          }
                        } catch (error) {
                          console.error('Version check failed:', error);
                          showToast('Version check failed - using cached version 1.0.0');
                        }
                      }}
                      className="flex items-center gap-2 px-4 py-2 rounded bg-muted hover:bg-muted/80 text-sm mb-3"
                    >
                      <RefreshCw className="w-4 h-4" />
                      Check for Updates
                    </button>
                  </div>

                  <div className="p-4 rounded-lg border bg-card">
                    <div className="font-medium mb-3">Resources</div>
                    <div className="space-y-2">
                      <a href="#" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
                        <FileText className="w-4 h-4" />
                        Licenses
                        <ExternalLink className="w-3 h-3" />
                      </a>
                      <a href="#" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
                        <HelpCircle className="w-4 h-4" />
                        Support & Contact
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Confirmation Dialog */}
          {showConfirmDialog && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
              <div className="bg-background p-6 rounded-lg border max-w-md">
                <h3 className="text-lg font-semibold mb-4">Confirm Action</h3>
                <p className="text-muted-foreground mb-6">{confirmMessage}</p>
                <div className="flex gap-3 justify-end">
                  <button 
                    onClick={() => setShowConfirmDialog(false)}
                    className="px-4 py-2 rounded bg-muted hover:bg-muted/80"
                  >
                    Cancel
                  </button>
                  <button 
                    onClick={() => { if (confirmAction) confirmAction(); setShowConfirmDialog(false); }}
                    className="px-4 py-2 rounded bg-red-500 hover:bg-red-600 text-white"
                  >
                    Confirm
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}