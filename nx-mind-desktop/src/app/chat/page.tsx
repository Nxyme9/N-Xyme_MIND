"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import {
  Send,
  Bot,
  User,
  Sparkles,
  Code,
  FileText,
  Terminal,
  Loader2,
  Copy,
  Trash2,
  RotateCcw,
  StopCircle,
  Settings,
  Plus,
  ChevronLeft,
  ChevronRight,
  Paperclip,
  X,
  MoreVertical,
  Search,
  Download,
  Edit3,
  Keyboard,
  FolderOpen,
  MessageSquare,
  File,
  Mic,
  Eye,
  EyeOff,
  Wand2,
  Sun,
  Moon,
  Upload,
  Link,
  Clock,
} from "lucide-react";
import { useChat } from "@/hooks/useChat";
import { NoChatsState } from "@/components/ui/empty-state";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  thinking?: string;
  tools?: string[];
  error?: string;
  reactions?: string[];
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}

interface ChatSettings {
  temperature: number;
  maxTokens: number;
  topP: number;
  presencePenalty: number;
  frequencyPenalty: number;
  systemPrompt: string;
}

// Chat model options
const chatModels = [
  { id: "gpt-4o", name: "GPT-4o" },
  { id: "gpt-4o-mini", name: "GPT-4o Mini" },
  { id: "claude-3-5-sonnet", name: "Claude 3.5 Sonnet" },
  { id: "claude-3-haiku", name: "Claude 3 Haiku" },
  { id: "gemini-1.5-pro", name: "Gemini 1.5 Pro" },
];

interface Attachment {
  id: string;
  name: string;
  type: string;
  size: number;
  content: string;
}

const quickActions = [
  { icon: Code, label: "Write code", prompt: "Write a React component" },
  { icon: FileText, label: "Explain", prompt: "Explain how this works" },
  { icon: Terminal, label: "Debug", prompt: "Debug this code" },
  { icon: Sparkles, label: "Refactor", prompt: "Refactor this code" },
];

const defaultSettings: ChatSettings = {
  temperature: 0.7,
  maxTokens: 4096,
  topP: 1,
  presencePenalty: 0,
  frequencyPenalty: 0,
  systemPrompt: "You are a helpful AI assistant.",
};

const keyboardShortcuts = [
  { keys: "Enter", action: "Send message" },
  { keys: "Shift+Enter", action: "New line" },
  { keys: "⌘K", action: "Command palette" },
  { keys: "⌘/", action: "Toggle shortcuts help" },
  { keys: "Escape", action: "Close modal" },
];

const fontSizeOptions = [
  { value: "12", label: "12px" },
  { value: "14", label: "14px (default)" },
  { value: "16", label: "16px" },
  { value: "18", label: "18px" },
  { value: "20", label: "20px" },
  { value: "24", label: "24px" },
];

// Load conversations from localStorage
const loadConversations = (): Conversation[] => {
  if (typeof window === "undefined") return [];
  const stored = localStorage.getItem("chat_conversations");
  if (!stored) return [];
  try {
    const parsed = JSON.parse(stored);
    return parsed.map((c: Conversation) => ({
      ...c,
      createdAt: new Date(c.createdAt),
      updatedAt: new Date(c.updatedAt),
      messages: c.messages.map((m: Message) => ({
        ...m,
        timestamp: new Date(m.timestamp),
      })),
    }));
  } catch {
    return [];
  }
};

// Save conversations to localStorage
const saveConversations = (conversations: Conversation[]) => {
  if (typeof window === "undefined") return;
  localStorage.setItem("chat_conversations", JSON.stringify(conversations));
};

// Load settings from localStorage
const loadSettings = (): ChatSettings => {
  if (typeof window === "undefined") return defaultSettings;
  const stored = localStorage.getItem("chat_settings");
  if (!stored) return defaultSettings;
  try {
    return { ...defaultSettings, ...JSON.parse(stored) };
  } catch {
    return defaultSettings;
  }
};

// Save settings to localStorage
const saveSettings = (settings: ChatSettings) => {
  if (typeof window === "undefined") return;
  localStorage.setItem("chat_settings", JSON.stringify(settings));
};

// Load theme from localStorage
const loadTheme = (): "light" | "dark" => {
  if (typeof window === "undefined") return "dark";
  const stored = localStorage.getItem("chat_theme");
  if (stored === "light" || stored === "dark") return stored;
  return "dark";
};

// Save theme to localStorage
const saveTheme = (theme: "light" | "dark") => {
  if (typeof window === "undefined") return;
  localStorage.setItem("chat_theme", theme);
};

// Load font size from localStorage
const loadFontSize = (): string => {
  if (typeof window === "undefined") return "14";
  const stored = localStorage.getItem("chat_font_size");
  if (stored) return stored;
  return "14";
};

// Save font size to localStorage
const saveFontSize = (fontSize: string) => {
  if (typeof window === "undefined") return;
  localStorage.setItem("chat_font_size", fontSize);
};

export default function ChatPage() {
  const { messages, isStreaming, currentModel, error, sendMessage, setModel, clearMessages, deleteMessage, updateMessageReactions, updateMessage, stopStreaming, regenerateResponse } = useChat({ initialModel: "gpt-4o" });
  const [input, setInput] = useState("");
  const [toast, setToast] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [settings, setSettings] = useState<ChatSettings>(defaultSettings);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");
  const [regeneratingId, setRegeneratingId] = useState<string | null>(null);
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);
  const [reactionsPickerOpen, setReactionsPickerOpen] = useState<string | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState<string | null>(null);
  const [deleteConversationConfirmOpen, setDeleteConversationConfirmOpen] = useState<string | null>(null);
  const [markdownPreview, setMarkdownPreview] = useState(false);
  const [voiceInput, setVoiceInput] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [speechError, setSpeechError] = useState<string | null>(null);
  const [liveTranscription, setLiveTranscription] = useState("");
  const [recordingDuration, setRecordingDuration] = useState(0);
  const recognitionRef = useRef<any>(null);
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const durationIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const [codeDetected, setCodeDetected] = useState(false);
  const [detectedLanguage, setDetectedLanguage] = useState<string>("");
  const [editingConversationId, setEditingConversationId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [conversationSearchQuery, setConversationSearchQuery] = useState("");
  const [theme, setTheme] = useState<"light" | "dark">("dark");
  const [fontSize, setFontSize] = useState("14");
  const [showTimestamps, setShowTimestamps] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const importInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Initialize from localStorage
  useEffect(() => {
    setConversations(loadConversations());
    setSettings(loadSettings());
    // Restore draft from localStorage
    const savedDraft = localStorage.getItem("chat_draft");
    if (savedDraft) {
      setInput(savedDraft);
    }
    // Load theme
    const savedTheme = loadTheme();
    setTheme(savedTheme);
    document.documentElement.classList.remove("light", "dark");
    document.documentElement.classList.add(savedTheme);
    // Load font size
    const savedFontSize = loadFontSize();
    setFontSize(savedFontSize);
  }, []);

  // Auto-save settings
  useEffect(() => {
    saveSettings(settings);
  }, [settings]);

  // Auto-save draft to localStorage on input change
  useEffect(() => {
    if (input) {
      localStorage.setItem("chat_draft", input);
    } else {
      localStorage.removeItem("chat_draft");
    }
  }, [input]);

  // Clear draft after successful send
  useEffect(() => {
    if (messages.length > 0 && messages[messages.length - 1].role === "user") {
      localStorage.removeItem("chat_draft");
    }
  }, [messages]);

  // New chat handler - defined early to avoid hoisting issues
  const handleNewChat = useCallback(() => {
    clearMessages();
    setCurrentConversationId(null);
    const newConversation: Conversation = {
      id: Date.now().toString(),
      title: "New Chat",
      messages: [],
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    setConversations((prev) => {
      const updated = [newConversation, ...prev];
      saveConversations(updated);
      return updated;
    });
    setCurrentConversationId(newConversation.id);
  }, [clearMessages, setCurrentConversationId, setConversations]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Close modal with Escape
      if (e.key === "Escape") {
        if (shortcutsOpen) {
          setShortcutsOpen(false);
          return;
        }
        if (settingsOpen) {
          setSettingsOpen(false);
          return;
        }
      }
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        // Command palette - could be expanded
      }
      if ((e.metaKey || e.ctrlKey) && e.key === "l") {
        e.preventDefault();
        handleNewChat();
      }
      if ((e.metaKey || e.ctrlKey) && e.key === "/") {
        e.preventDefault();
        setShortcutsOpen(true);
      }
      if (e.key === "ArrowUp" && inputRef.current && !editingMessageId) {
        const lastUserMessage = [...messages].reverse().find(m => m.role === "user");
        if (lastUserMessage) {
          setEditingMessageId(lastUserMessage.id);
          setEditContent(lastUserMessage.content);
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [messages, editingMessageId, shortcutsOpen, settingsOpen]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Drag and drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const files = Array.from(e.dataTransfer.files);
    handleFiles(files);
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    handleFiles(files);
  };

  const handleFiles = (files: File[]) => {
    // Supported file types
    const supportedTypes = [".txt", ".md", ".js", ".ts", ".py", ".json", ".png", ".jpg", ".jpeg", ".gif"];
    
    files.forEach((file) => {
      const ext = "." + file.name.split(".").pop()?.toLowerCase();
      if (!supportedTypes.includes(ext)) {
        setToast(`Unsupported file type: ${ext}`);
        setTimeout(() => setToast(null), 2000);
        return;
      }
      
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = ext !== ".png" && ext !== ".jpg" && ext !== ".jpeg" && ext !== ".gif" 
          ? (e.target?.result as string) 
          : "";
        
        // Detect language from extension
        let language = "";
        const langMap: Record<string, string> = {
          ".js": "javascript", ".ts": "typescript", ".py": "python", ".json": "json",
          ".md": "markdown", ".txt": "text"
        };
        if (langMap[ext]) language = langMap[ext];
        
        const attachment: Attachment = {
          id: Date.now().toString() + Math.random(),
          name: file.name,
          type: file.type,
          size: file.size,
          content,
        };
        setAttachments((prev) => [...prev, attachment]);
        
        // Auto-detect code if attaching code file
        if (language && language !== "text" && language !== "image") {
          setCodeDetected(true);
          setDetectedLanguage(language);
        }
      };
      
      // Only read text files as text, images skip content read
      if ([".txt", ".md", ".js", ".ts", ".py", ".json"].includes(ext)) {
        reader.readAsText(file);
      }
    });
  };

  // Paste handler
  const handlePaste = (e: React.ClipboardEvent) => {
    const items = Array.from(e.clipboardData.items);
    const files = items
      .filter((item) => item.kind === "file")
      .map((item) => item.getAsFile())
      .filter((f): f is File => f !== null);
    if (files.length > 0) {
      handleFiles(files);
    }
  };

  const removeAttachment = (id: string) => {
    setAttachments((prev) => prev.filter((a) => a.id !== id));
  };

  const handleSend = async () => {
    if (!input.trim() && attachments.length === 0) return;
    if (isStreaming) return;

    // Include attachments in message if any
    let fullContent = input;
    if (attachments.length > 0) {
      const attachmentText = attachments
        .map((a) => `\`\`\`${a.name}\n${a.content}\n\`\`\``)
        .join("\n\n");
      fullContent = `${attachmentText}\n\n${input}`;
    }

    await sendMessage(fullContent);
    setInput("");
    setAttachments([]);

    // Save conversation
    if (currentConversationId) {
      setConversations((prev) => {
        const updated = prev.map((c) =>
          c.id === currentConversationId
            ? { ...c, messages: [...c.messages, { id: Date.now().toString(), role: "user" as const, content: fullContent, timestamp: new Date() }], updatedAt: new Date() }
            : c
        );
        saveConversations(updated);
        return updated;
      });
    }
  };

  const handleQuickAction = (prompt: string) => {
    setInput(prompt);
  };

  const handleCopyMessage = (content: string) => {
    navigator.clipboard.writeText(content);
    setToast("Copied!");
    setTimeout(() => setToast(null), 2000);
  };

  const handleSelectConversation = (conv: Conversation) => {
    setCurrentConversationId(conv.id);
    // Load messages for this conversation - would need to extend useChat hook
  };

  const handleDeleteConversation = (id: string) => {
    setDeleteConversationConfirmOpen(id);
  };

  const confirmDeleteConversation = () => {
    if (!deleteConversationConfirmOpen) return;
    setConversations((prev) => {
      const updated = prev.filter((c) => c.id !== deleteConversationConfirmOpen);
      saveConversations(updated);
      return updated;
    });
    if (currentConversationId === deleteConversationConfirmOpen) {
      handleNewChat();
    }
    setDeleteConversationConfirmOpen(null);
    setToast("Conversation deleted");
    setTimeout(() => setToast(null), 2000);
  };

  const handleStartRename = (id: string, currentTitle: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingConversationId(id);
    setEditingTitle(currentTitle);
  };

  const handleSaveRename = (id: string) => {
    if (!editingTitle.trim()) {
      setEditingConversationId(null);
      return;
    }
    setConversations((prev) => {
      const updated = prev.map((c) =>
        c.id === id ? { ...c, title: editingTitle.trim(), updatedAt: new Date() } : c
      );
      saveConversations(updated);
      return updated;
    });
    setEditingConversationId(null);
    setToast("Conversation renamed");
    setTimeout(() => setToast(null), 2000);
  };

  const handleExport = (conv: Conversation, format: "json" | "markdown", e: React.MouseEvent) => {
    e.stopPropagation();
    let content: string;
    let filename: string;
    let mimeType: string;

    if (format === "json") {
      content = JSON.stringify(
        {
          id: conv.id,
          title: conv.title,
          createdAt: conv.createdAt.toISOString(),
          updatedAt: conv.updatedAt.toISOString(),
          messages: conv.messages.map((m) => ({
            id: m.id,
            role: m.role,
            content: m.content,
            timestamp: m.timestamp.toISOString(),
          })),
        },
        null,
        2
      );
      filename = `${conv.title.replace(/[^a-z0-9]/gi, "_")}.json`;
      mimeType = "application/json";
    } else {
      content = `# ${conv.title}\n\nCreated: ${conv.createdAt.toLocaleString()}\n\n---\n\n${conv.messages
  .map((m) => `## ${m.role === "user" ? "You" : "Assistant"}\n\n${m.content}\n\n*${m.timestamp.toLocaleString()}*`)
  .join("\n\n---\n\n")}`;
      filename = `${conv.title.replace(/[^a-z0-9]/gi, "_")}.md`;
      mimeType = "text/markdown";
    }

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    setToast(`Exported as ${format.toUpperCase()}`);
    setTimeout(() => setToast(null), 2000);
  };

  const filteredMessages = conversationSearchQuery
    ? messages.filter((m) => m.content.toLowerCase().includes(conversationSearchQuery.toLowerCase()))
    : messages;

  const handleEditMessage = (messageId: string, newContent: string) => {
    // Find and update the message, then resend
    const message = messages.find((m) => m.id === messageId);
    if (message) {
      setInput(newContent);
      deleteMessage(messageId);
    }
    setEditingMessageId(null);
    setEditContent("");
  };

  const handleRegenerate = (messageId: string) => {
    const message = messages.find((m) => m.id === messageId);
    if (message) {
      deleteMessage(messageId);
      // Find previous user message and resend
      const messageIndex = messages.findIndex((m) => m.id === messageId);
      if (messageIndex > 0) {
        const prevMessage = messages[messageIndex - 1];
        if (prevMessage.role === "user") {
          // Show regenerating state
          setRegeneratingId(messageId);
          sendMessage(prevMessage.content).then(() => {
            setRegeneratingId(null);
          });
        }
      }
    }
    setMenuOpenId(null);
  };

  const handleAddReaction = (messageId: string, emoji: string) => {
    const msg = messages.find(m => m.id === messageId);
    if (msg) {
      const currentReactions = msg.reactions || [];
      const newReactions = currentReactions.includes(emoji)
        ? currentReactions.filter(r => r !== emoji)
        : [...currentReactions, emoji];
      updateMessageReactions(messageId, newReactions);
      setToast(emoji === currentReactions[0] ? `Removed ${emoji}` : `Added ${emoji}`);
      setTimeout(() => setToast(null), 1500);
    }
    setReactionsPickerOpen(null);
  };

  const handleDeleteMessage = (messageId: string) => {
    deleteMessage(messageId);
    setDeleteConfirmOpen(null);
    setToast("Message deleted");
    setTimeout(() => setToast(null), 1500);
  };

  const handleRetryMessage = (messageId: string) => {
    const messageIndex = messages.findIndex((m) => m.id === messageId);
    if (messageIndex > 0) {
      const prevMessage = messages[messageIndex - 1];
      if (prevMessage.role === "user") {
        deleteMessage(messageId);
        sendMessage(prevMessage.content);
      }
    }
  };

  // Toggle theme
  const toggleTheme = () => {
    const newTheme = theme === "dark" ? "light" : "dark";
    setTheme(newTheme);
    saveTheme(newTheme);
    document.documentElement.classList.remove("light", "dark");
    document.documentElement.classList.add(newTheme);
  };

  // Handle font size change
  const handleFontSizeChange = (newSize: string) => {
    setFontSize(newSize);
    saveFontSize(newSize);
  };

  // Handle import conversation
  const handleImportConversation = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const content = event.target?.result as string;
        let importedConversation: Conversation;

        if (file.name.endsWith(".json")) {
          const parsed = JSON.parse(content);
          importedConversation = {
            id: Date.now().toString(),
            title: parsed.title || "Imported Chat",
            messages: (parsed.messages || []).map((m: any) => ({
              id: m.id || Date.now().toString() + Math.random(),
              role: m.role || "user",
              content: m.content || "",
              timestamp: new Date(m.timestamp || Date.now()),
            })),
            createdAt: new Date(parsed.createdAt || Date.now()),
            updatedAt: new Date(),
          };
        } else {
          // Markdown import - create simple conversation
          const lines = content.split("\n");
          const titleMatch = lines.find((l) => l.startsWith("# "));
          importedConversation = {
            id: Date.now().toString(),
            title: titleMatch ? titleMatch.replace("# ", "") : "Imported Chat",
            messages: [],
            createdAt: new Date(),
            updatedAt: new Date(),
          };
        }

        setConversations((prev) => {
          const updated = [importedConversation, ...prev];
          saveConversations(updated);
          return updated;
        });
        setToast("Conversation imported successfully!");
        setTimeout(() => setToast(null), 2000);
      } catch (err) {
        setToast("Failed to import conversation");
        setTimeout(() => setToast(null), 2000);
      }
    };
    reader.readAsText(file);
    // Reset input
    e.target.value = "";
  };

  // Handle share conversation
  const handleShareConversation = (conv: Conversation, e: React.MouseEvent) => {
    e.stopPropagation();
    const shareId = Math.random().toString(36).substring(2, 10);
    const shareLink = `https://nxyme.app/share/${shareId}`;
    navigator.clipboard.writeText(shareLink);
    setToast("Link copied!");
    setTimeout(() => setToast(null), 2000);
  };

  // Check for Web Speech API support
  const isSpeechRecognitionSupported = (): boolean => {
    return typeof window !== "undefined" && 
      ("SpeechRecognition" in window || "webkitSpeechRecognition" in window);
  };

  // Voice input handler
  const handleVoiceInput = useCallback(() => {
    if (!isSpeechRecognitionSupported()) {
      setSpeechError("Voice input requires Chrome/Edge/Safari");
      setTimeout(() => setSpeechError(null), 3000);
      return;
    }

    if (voiceInput) {
      // Stop listening
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setVoiceInput(false);
      setIsListening(false);
      setLiveTranscription("");
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current);
        silenceTimerRef.current = null;
      }
      if (durationIntervalRef.current) {
        clearInterval(durationIntervalRef.current);
        durationIntervalRef.current = null;
      }
      setRecordingDuration(0);
      return;
    }

    // Start listening
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onstart = () => {
      setVoiceInput(true);
      setIsListening(true);
      setSpeechError(null);
      setLiveTranscription("");
      setRecordingDuration(0);
      
      // Start duration timer
      durationIntervalRef.current = setInterval(() => {
        setRecordingDuration((prev) => prev + 1);
      }, 1000);
    };

    recognition.onresult = (event: any) => {
      let finalTranscript = "";
      let interimTranscript = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interimTranscript += transcript;
        }
      }

      // Update input with interim results
      const currentInput = finalTranscript || interimTranscript;
      setLiveTranscription(currentInput);
      setInput(input + currentInput);

      // Reset silence timer on speech
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current);
      }

      // Auto-stop on punctuation
      if (finalTranscript && /[.!?]$/.test(finalTranscript.trim())) {
        recognition.stop();
        return;
      }

      // Start silence timer (3 seconds)
      silenceTimerRef.current = setTimeout(() => {
        recognition.stop();
      }, 3000);
    };

    recognition.onerror = (event: any) => {
      console.error("Speech recognition error:", event.error);
      
      let errorMessage = "";
      switch (event.error) {
        case "not-allowed":
          errorMessage = "Please allow microphone access";
          break;
        case "network":
          errorMessage = "Could not recognize speech";
          break;
        case "no-speech":
          errorMessage = "No speech detected";
          break;
        case "aborted":
          // User manually stopped, not an error
          break;
        default:
          errorMessage = "Speech recognition error";
      }
      
      if (errorMessage) {
        setSpeechError(errorMessage);
        setTimeout(() => setSpeechError(null), 3000);
      }
      
      setVoiceInput(false);
      setIsListening(false);
      if (durationIntervalRef.current) {
        clearInterval(durationIntervalRef.current);
        durationIntervalRef.current = null;
      }
      setRecordingDuration(0);
    };

    recognition.onend = () => {
      setVoiceInput(false);
      setIsListening(false);
      if (durationIntervalRef.current) {
        clearInterval(durationIntervalRef.current);
        durationIntervalRef.current = null;
      }
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current);
        silenceTimerRef.current = null;
      }
    };

    recognitionRef.current = recognition;
    recognition.start();
  }, [voiceInput, input]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current);
      }
      if (durationIntervalRef.current) {
        clearInterval(durationIntervalRef.current);
      }
    };
  }, []);

  // Format duration for display
  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const extractCodeBlocks = (content: string): string[] => {
    const codeBlocks: string[] = [];
    const regex = /```(\w+)?\n([\s\S]*?)```/g;
    let match;
    while ((match = regex.exec(content)) !== null) {
      codeBlocks.push(match[2]);
    }
    return codeBlocks;
  };

  // Detect code in input
  const detectCode = useCallback((text: string): { isCode: boolean; language: string } => {
    if (!text || text.length < 10) return { isCode: false, language: "" };
    
    const lines = text.split("\n");
    const hasMultipleLines = lines.length >= 2;
    const hasBraces = /\{|\}/.test(text);
    const hasFunction = /\bfunction\s+\w+|def\s+\w+|\bfunc\s+\w+|fn\s+\w+/.test(text);
    const hasClass = /\bclass\s+\w+/.test(text);
    const hasImport = /\bimport\s+|require\s+|from\s+.*\s+import/.test(text);
    const hasArrow = /=>/.test(text);
    const hasConstLetVar = /\b(const|let|var)\s+/.test(text);
    
    const codeIndicators = [hasBraces, hasFunction, hasClass, hasImport, hasArrow, hasConstLetVar].filter(Boolean).length;
    
    const isCode = hasMultipleLines && codeIndicators >= 2;
    
    // Detect language from content
    let language = "";
    if (/import\s+{|export\s+|const\s+\w+\s+=|let\s+\w+\s+=|var\s+\w+\s+=/.test(text)) {
      language = "javascript";
    } else if (/def\s+\w+\s*\(|import\s+\w+|from\s+\w+\s+import/.test(text)) {
      language = "python";
    } else if (/func\s+\w+|\bfunc\b|type\s+\w+\s+struct/.test(text)) {
      language = "go";
    } else if (/public\s+class|private\s+|void\s+\w+/.test(text)) {
      language = "java";
    }
    
    return { isCode, language };
  }, []);

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {/* Sidebar */}
      <div
        className={`border-r bg-background transition-all duration-300 ${
          sidebarOpen ? "w-72" : "w-0 overflow-hidden"
        }`}
      >
        <div className="p-4 h-full flex flex-col">
          {/* New Chat Button */}
          <div className="flex gap-2 mb-4">
            <Button onClick={handleNewChat} className="flex-1">
              <Plus className="w-4 h-4 mr-2" />
              New Chat
            </Button>
            <Button
              variant="outline"
              size="icon"
              onClick={() => importInputRef.current?.click()}
              title="Import conversation"
            >
              <Upload className="w-4 h-4" />
            </Button>
            <input
              ref={importInputRef}
              type="file"
              accept=".json,.md"
              className="hidden"
              onChange={handleImportConversation}
            />
            <Button
              variant="outline"
              size="icon"
              onClick={() => setConversationSearchQuery(conversationSearchQuery ? "" : "filter")}
              title="Filter messages"
              className={conversationSearchQuery ? "bg-accent" : ""}
            >
              <Search className="w-4 h-4" />
            </Button>
          </div>

          {/* Search within conversation */}
          {conversationSearchQuery && (
            <div className="relative mb-2">
              <Search className="w-4 h-4 absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search messages..."
                value={conversationSearchQuery}
                onChange={(e) => setConversationSearchQuery(e.target.value)}
                className="pl-8 h-8 text-sm"
              />
              {conversationSearchQuery && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute right-0 top-1/2 -translate-y-1/2 h-6 w-6"
                  onClick={() => setConversationSearchQuery("")}
                >
                  <X className="w-3 h-3" />
                </Button>
              )}
            </div>
          )}

          {/* Conversations List */}
          <div className="flex-1 overflow-y-auto space-y-2">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                className={`group flex items-center justify-between p-2 rounded-lg cursor-pointer hover:bg-accent ${
                  currentConversationId === conv.id ? "bg-accent" : ""
                }`}
                onClick={() => handleSelectConversation(conv)}
              >
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  <MessageSquare className="w-4 h-4 flex-shrink-0" />
                  {editingConversationId === conv.id ? (
                    <Input
                      value={editingTitle}
                      onChange={(e) => setEditingTitle(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleSaveRename(conv.id);
                        if (e.key === "Escape") setEditingConversationId(null);
                      }}
                      onBlur={() => handleSaveRename(conv.id)}
                      onClick={(e) => e.stopPropagation()}
                      className="h-6 text-sm flex-1 min-w-0"
                      autoFocus
                    />
                  ) : (
                    <span
                      className="truncate text-sm hover:text-primary"
                      onClick={(e) => handleStartRename(conv.id, conv.title, e)}
                      title="Click to rename"
                    >
                      {conv.title}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  {/* Share Button */}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 opacity-0 group-hover:opacity-100"
                    onClick={(e) => handleShareConversation(conv, e)}
                    title="Share"
                  >
                    <Link className="w-3 h-3" />
                  </Button>
                  {/* Export Button */}
                  <div className="relative">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 opacity-0 group-hover:opacity-100"
                      onClick={(e) => {
                        e.stopPropagation();
                        setMenuOpenId(menuOpenId === `export-${conv.id}` ? null : `export-${conv.id}`);
                      }}
                    >
                      <Download className="w-3 h-3" />
                    </Button>
                    {menuOpenId === `export-${conv.id}` && (
                      <div className="absolute right-0 top-8 bg-background border rounded-lg shadow-lg z-20 py-1 min-w-[120px]">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="w-full justify-start text-xs"
                          onClick={(e) => handleExport(conv, "json", e)}
                        >
                          <File className="w-3 h-3 mr-2" />
                          Export JSON
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="w-full justify-start text-xs"
                          onClick={(e) => handleExport(conv, "markdown", e)}
                        >
                          <FileText className="w-3 h-3 mr-2" />
                          Export Markdown
                        </Button>
                      </div>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 opacity-0 group-hover:opacity-100"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteConversation(conv.id);
                    }}
                  >
                    <Trash2 className="w-3 h-3" />
                  </Button>
                </div>
              </div>
            ))}
            {conversations.length === 0 && (
              <NoChatsState onCreate={handleNewChat} />
            )}
          </div>

          {/* Folders Section */}
          <div className="mt-4 pt-4 border-t">
            <Button variant="ghost" size="sm" className="w-full justify-start">
              <FolderOpen className="w-4 h-4 mr-2" />
              Folders
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        <div className="container mx-auto py-4 h-full">
          <div className="flex flex-col h-full max-w-4xl mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setSidebarOpen(!sidebarOpen)}
                >
                  {sidebarOpen ? (
                    <ChevronLeft className="w-5 h-5" />
                  ) : (
                    <ChevronRight className="w-5 h-5" />
                  )}
                </Button>
                <Bot className="w-6 h-6" />
                <h1 className="text-xl font-bold">AI Chat</h1>
                <Badge variant="outline" className="text-xs">
                  Sisyphus
                </Badge>
              </div>
              <div className="flex items-center gap-2">
                <Badge
                  variant="secondary"
                  className="bg-green-500/20 text-green-500 border-0"
                >
                  Online
                </Badge>
                <select
                  value={currentModel}
                  onChange={(e) => setModel(e.target.value)}
                  className="h-8 px-2 text-sm bg-background border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  {chatModels.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name}
                    </option>
                  ))}
                </select>
                {/* Timestamp Toggle */}
                <Button
                  variant={showTimestamps ? "default" : "ghost"}
                  size="icon"
                  onClick={() => setShowTimestamps(!showTimestamps)}
                  title={showTimestamps ? "Hide timestamps" : "Show timestamps"}
                >
                  <Clock className="w-5 h-5" />
                </Button>
                {/* Font Size Selector */}
                <select
                  value={fontSize}
                  onChange={(e) => handleFontSizeChange(e.target.value)}
                  className="h-8 px-2 text-sm bg-background border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                  title="Font size"
                >
                  {fontSizeOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                {/* Theme Toggle */}
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={toggleTheme}
                  title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
                >
                  {theme === "dark" ? (
                    <Sun className="w-5 h-5" />
                  ) : (
                    <Moon className="w-5 h-5" />
                  )}
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setSettingsOpen(true)}
                >
                  <Settings className="w-5 h-5" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setShortcutsOpen(true)}
                >
                  <Keyboard className="w-5 h-5" />
                </Button>
              </div>
            </div>

            {/* Messages */}
            <Card className="flex-1 overflow-hidden mb-4">
              <CardContent className="p-4 h-full overflow-y-auto space-y-4">
                {conversationSearchQuery && (
                  <div className="text-sm text-muted-foreground pb-2 border-b">
                    Found {filteredMessages.length} of {messages.length} messages
                  </div>
                )}
                {filteredMessages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex gap-3 ${
                      message.role === "user" ? "flex-row-reverse" : ""
                    }`}
                  >
                    <Avatar className="w-8 h-8">
                      {message.role === "assistant" ? (
                        <>
                          <AvatarImage src="/bot-avatar.png" />
                          <AvatarFallback className="bg-blue-500 text-white">
                            <Bot className="w-4 h-4" />
                          </AvatarFallback>
                        </>
                      ) : (
                        <>
                          <AvatarImage src="/user-avatar.png" />
                          <AvatarFallback className="bg-gray-500 text-white">
                            <User className="w-4 h-4" />
                          </AvatarFallback>
                        </>
                      )}
                    </Avatar>
                    <div
                      className={`flex-1 ${message.role === "user" ? "text-right" : ""}`}
                    >
                      <div
                        className={`inline-block max-w-[80%] rounded-lg px-4 py-2 ${
                          message.role === "user"
                            ? "bg-blue-500 text-white"
                            : "bg-muted"
                        }`}
                        style={{ fontSize: `${fontSize}px` }}
                      >
                        {message.role === "assistant" ? (
                          <div className="text-sm">
                            <ReactMarkdown
                              components={{
                                code({ className, children, ...props }) {
                                  const match = /language-(\w+)/.exec(
                                    className || ""
                                  );
                                  const isInline = !match && !String(children).includes("\n");
                                  return isInline ? (
                                    <code
                                      className="bg-gray-800 text-pink-300 px-1 rounded"
                                      {...props}
                                    >
                                      {children}
                                    </code>
                                  ) : (
                                    <SyntaxHighlighter
                                      style={oneDark}
                                      language={match ? match[1] : "text"}
                                      PreTag="div"
                                      className="rounded-md text-sm"
                                    >
                                      {String(children).replace(/\n$/, "")}
                                    </SyntaxHighlighter>
                                  );
                                },
                                table({ children }) {
                                  return (
                                    <div className="overflow-x-auto">
                                      <table className="w-full border-collapse text-sm">
                                        {children}
                                      </table>
                                    </div>
                                  );
                                },
                                th({ children }) {
                                  return (
                                    <th className="border px-2 py-1 text-left bg-gray-800">
                                      {children}
                                    </th>
                                  );
                                },
                                td({ children }) {
                                  return (
                                    <td className="border px-2 py-1 text-left">
                                      {children}
                                    </td>
                                  );
                                },
                              }}
                            >
                              {message.content}
                            </ReactMarkdown>
                          </div>
                        ) : message.role === "user" && editingMessageId === message.id ? (
                          <div className="flex flex-col gap-2">
                            <textarea
                              value={editContent}
                              onChange={(e) => setEditContent(e.target.value)}
                              className="w-full h-24 p-2 border rounded-md bg-background text-foreground resize-none"
                              autoFocus
                            />
                            <div className="flex gap-2 justify-end">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => {
                                  setEditingMessageId(null);
                                  setEditContent("");
                                }}
                              >
                                Cancel
                              </Button>
                              <Button
                                size="sm"
                                onClick={() => {
                                  handleEditMessage(message.id, editContent);
                                }}
                              >
                                Save
                              </Button>
                            </div>
                          </div>
                        ) : (
                          <p className="whitespace-pre-wrap">{message.content}</p>
                        )}
                      </div>
                      {message.thinking && (
                        <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                          <span className="animate-pulse">🤔</span>
                          {message.thinking}
                        </p>
                      )}
                      {message.tools && message.tools.length > 0 && (
                        <div className="flex gap-1 mt-2">
                          {message.tools.map((tool) => (
                            <Badge key={tool} variant="outline" className="text-xs">
                              {tool}
                            </Badge>
                          ))}
                        </div>
                      )}
                      {showTimestamps && (
                        <p className="text-xs text-muted-foreground mt-1">
                          {message.timestamp.toLocaleTimeString()}
                        </p>
                      )}
                      {/* Message Reactions Display */}
                      {message.reactions && message.reactions.length > 0 && (
                        <div className="flex gap-1 mt-1">
                          {message.reactions.map((reaction, idx) => (
                            <span key={idx} className="text-sm cursor-pointer hover:scale-110 transition-transform">
                              {reaction}
                            </span>
                          ))}
                        </div>
                      )}
                      <div className="flex gap-1 mt-1 relative">
                        {/* Reaction Picker Button */}
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6"
                          onClick={() => setReactionsPickerOpen(reactionsPickerOpen === message.id ? null : message.id)}
                        >
                          <span className="text-xs">😀</span>
                        </Button>
                        {reactionsPickerOpen === message.id && (
                          <div className="absolute top-8 left-0 bg-background border rounded-lg shadow-lg z-10 py-1 flex gap-1">
                            {["👍", "👎", "❤️", "🎉"].map((emoji) => (
                              <button
                                key={emoji}
                                className="hover:bg-accent px-2 py-1 rounded text-lg"
                                onClick={() => handleAddReaction(message.id, emoji)}
                              >
                                {emoji}
                              </button>
                            ))}
                          </div>
                        )}
                        {/* Copy Button */}
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6"
                          onClick={() => handleCopyMessage(message.content)}
                        >
                          <Copy className="w-3 h-3" />
                        </Button>
                        {/* Edit Button for User Messages */}
                        {message.role === "user" && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6"
                            onClick={() => {
                              setEditingMessageId(message.id);
                              setEditContent(message.content);
                            }}
                          >
                            <Edit3 className="w-3 h-3" />
                          </Button>
                        )}
                        {/* Retry Button for Failed Messages */}
                        {message.error && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6 text-orange-500 hover:text-orange-600"
                            onClick={() => handleRetryMessage(message.id)}
                          >
                            <RotateCcw className="w-3 h-3" />
                          </Button>
                        )}
                        {message.role === "assistant" && (
                          <>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-6 w-6"
                              onClick={() => handleRegenerate(message.id)}
                            >
                              <RotateCcw className="w-3 h-3" />
                            </Button>
                            <div className="relative">
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-6 w-6"
                                onClick={() =>
                                  setMenuOpenId(
                                    menuOpenId === message.id ? null : message.id
                                  )
                                }
                              >
                                <MoreVertical className="w-3 h-3" />
                              </Button>
                              {menuOpenId === message.id && (
                                <div className="absolute top-8 left-0 bg-background border rounded-lg shadow-lg z-10 py-1 min-w-[160px]">
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="w-full justify-start"
                                    onClick={() => {
                                      const codeBlocks = extractCodeBlocks(
                                        message.content
                                      );
                                      if (codeBlocks.length > 0) {
                                        handleCopyMessage(codeBlocks[0]);
                                      }
                                      setMenuOpenId(null);
                                    }}
                                  >
                                    <Code className="w-3 h-3 mr-2" />
                                    Copy code only
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="w-full justify-start"
                                    onClick={() => {
                                      handleCopyMessage(message.content);
                                      setMenuOpenId(null);
                                    }}
                                  >
                                    <Copy className="w-3 h-3 mr-2" />
                                    Copy with formatting
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="w-full justify-start"
                                    onClick={() => handleRegenerate(message.id)}
                                  >
                                    <RotateCcw className="w-3 h-3 mr-2" />
                                    Regenerate
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="w-full justify-start"
                                    onClick={() => {
                                      setEditingMessageId(message.id);
                                      setEditContent(message.content);
                                      setMenuOpenId(null);
                                    }}
                                  >
                                    <Edit3 className="w-3 h-3 mr-2" />
                                    Edit and resubmit
                                  </Button>
                                </div>
                              )}
                            </div>
                          </>
                        )}
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6 text-red-500 hover:text-red-600"
                          onClick={() => setDeleteConfirmOpen(message.id)}
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
                {isStreaming && (
                  <div className="flex gap-3">
                    <Avatar className="w-8 h-8">
                      <AvatarFallback className="bg-blue-500 text-white">
                        <Bot className="w-4 h-4" />
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <span className="animate-bounce">💭</span>
                      <span className="text-sm">Thinking...</span>
                    </div>
                  </div>
                )}
                {regeneratingId && !isStreaming && (
                  <div className="flex gap-3">
                    <Avatar className="w-8 h-8">
                      <AvatarFallback className="bg-blue-500 text-white">
                        <Bot className="w-4 h-4" />
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span className="text-sm">Regenerating...</span>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </CardContent>
            </Card>

            {/* Edit Message Modal (for assistant messages only - user messages have inline editing) */}
            {editingMessageId && messages.find(m => m.id === editingMessageId && m.role === "assistant") && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                <div className="bg-background p-4 rounded-lg max-w-lg w-full mx-4">
                  <h3 className="font-semibold mb-2">Edit Message</h3>
                  <textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    className="w-full h-32 p-2 border rounded-md bg-background"
                    placeholder="Edit your message..."
                  />
                  <div className="flex gap-2 mt-2 justify-end">
                    <Button
                      variant="outline"
                      onClick={() => {
                        setEditingMessageId(null);
                        setEditContent("");
                      }}
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={() => {
                        handleEditMessage(editingMessageId, editContent);
                      }}
                    >
                      Send
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {/* Toast */}
            {toast && (
              <div className="fixed bottom-20 left-1/2 -translate-x-1/2 bg-black text-white px-4 py-2 rounded-lg text-sm">
                {toast}
              </div>
            )}

            {/* Attachments Preview */}
            {attachments.length > 0 && (
              <div className="flex gap-2 mb-2 flex-wrap">
                {attachments.map((att) => (
                  <div
                    key={att.id}
                    className="flex items-center gap-1 bg-secondary px-2 py-1 rounded-md text-sm"
                  >
                    <File className="w-3 h-3" />
                    <span className="max-w-[100px] truncate">{att.name}</span>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-4 w-4"
                      onClick={() => removeAttachment(att.id)}
                    >
                      <X className="w-3 h-3" />
                    </Button>
                  </div>
                ))}
              </div>
            )}

            {/* Quick Actions */}
            <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
              {quickActions.map((action) => (
                <Button
                  key={action.label}
                  variant="outline"
                  size="sm"
                  onClick={() => handleQuickAction(action.prompt)}
                  className="flex items-center gap-2 whitespace-nowrap"
                >
                  <action.icon className="w-4 h-4" />
                  {action.label}
                </Button>
              ))}
            </div>

            {/* Input */}
            <div
              className="flex gap-2"
              onDragOver={handleDragOver}
              onDrop={handleDrop}
            >
              <input
                type="file"
                ref={fileInputRef}
                className="hidden"
                multiple
                onChange={handleFileSelect}
              />
              <Button
                variant="outline"
                size="icon"
                onClick={() => fileInputRef.current?.click()}
                title="Attach file"
              >
                <Paperclip className="w-4 h-4" />
              </Button>
              <Button
                variant={isListening ? "default" : "outline"}
                size="icon"
                onClick={handleVoiceInput}
                title={isListening ? "Stop listening" : "Voice input"}
                className={isListening ? "bg-red-500 hover:bg-red-600 animate-pulse" : ""}
              >
                <Mic className="w-4 h-4" />
                {isListening && (
                  <span className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                )}
              </Button>
              {speechError && (
                <span className="text-xs text-red-500 animate-pulse">{speechError}</span>
              )}
              {isListening && (
                <div className="flex items-center gap-1 text-xs text-red-500">
                  <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                  <span>Listening... {formatDuration(recordingDuration)}</span>
                </div>
              )}
              {input.trim() && (
                <Button
                  variant={markdownPreview ? "default" : "outline"}
                  size="icon"
                  onClick={() => setMarkdownPreview(!markdownPreview)}
                  title={markdownPreview ? "Hide preview" : "Show preview"}
                >
                  {markdownPreview ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </Button>
              )}
              {input.trim() && markdownPreview && (
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => {
                    handleSend();
                    setMarkdownPreview(false);
                  }}
                  title="Send with preview"
                >
                  <Wand2 className="w-4 h-4" />
                </Button>
              )}
              {markdownPreview && input.trim() ? (
                <div className="flex-1 border rounded-md p-3 bg-muted/30 max-h-[200px] overflow-y-auto">
                  <ReactMarkdown
                    components={{
                      code({ className, children, ...props }) {
                        const match = /language-(\w+)/.exec(className || "");
                        const isInline = !match && !String(children).includes("\n");
                        return isInline ? (
                          <code className="bg-gray-800 text-pink-300 px-1 rounded" {...props}>
                            {children}
                          </code>
                        ) : (
                          <SyntaxHighlighter
                            style={oneDark}
                            language={match ? match[1] : "text"}
                            PreTag="div"
                            className="rounded-md text-sm"
                          >
                            {String(children).replace(/\n$/, "")}
                          </SyntaxHighlighter>
                        );
                      },
                    }}
                  >
                    {input}
                  </ReactMarkdown>
                </div>
              ) : (
                <Input
                  ref={inputRef}
                  placeholder="Type your message..."
                  value={input}
                  onChange={(e) => {
                    setInput(e.target.value);
                    const { isCode, language } = detectCode(e.target.value);
                    setCodeDetected(isCode);
                    setDetectedLanguage(language);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  onPaste={handlePaste}
                  disabled={isStreaming}
                  className="flex-1"
                />
              )}
              {isStreaming ? (
                <Button onClick={stopStreaming} variant="destructive">
                  <StopCircle className="w-4 h-4 mr-2" />
                  Stop
                </Button>
              ) : (
                <>
                  {/* Code detected hint */}
                  {codeDetected && (
                    <div className="flex items-center gap-2 text-xs text-muted-foreground bg-muted/50 px-2 py-1 rounded">
                      <Code className="w-3 h-3" />
                      {detectedLanguage ? (
                        <span>Code detected ({detectedLanguage})</span>
                      ) : (
                        <span>Code detected</span>
                      )}
                    </div>
                  )}
                  <Button onClick={handleSend} disabled={!input.trim() && attachments.length === 0}>
                    <Send className="w-4 h-4" />
                  </Button>
                </>
              )}
            </div>

            {/* Character/Word Count */}
            {input.trim() && (
              <div className="flex justify-end gap-4 mt-1 text-xs text-muted-foreground">
                <span>{input.length} characters</span>
                <span>{input.trim().split(/\s+/).filter(Boolean).length} words</span>
              </div>
            )}

            <p className="text-xs text-muted-foreground text-center mt-2">
              Press Enter to send, Shift+Enter for new line • Drag & drop files or paste from clipboard
            </p>
          </div>
        </div>
      </div>

      {/* Settings Dialog */}
      <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Model Settings</DialogTitle>
            <DialogDescription>
              Configure your chat model parameters.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {/* Temperature */}
            <div className="space-y-2">
              <label className="text-sm font-medium">
                Temperature: {settings.temperature}
              </label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={settings.temperature}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    temperature: parseFloat(e.target.value),
                  })
                }
                className="w-full"
              />
              <p className="text-xs text-muted-foreground">
                Higher values make output more random, lower values more focused.
              </p>
            </div>

            {/* Max Tokens */}
            <div className="space-y-2">
              <label className="text-sm font-medium">
                Max Tokens: {settings.maxTokens}
              </label>
              <Input
                type="number"
                value={settings.maxTokens}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    maxTokens: parseInt(e.target.value) || 2048,
                  })
                }
                min={1}
                max={8192}
              />
              <p className="text-xs text-muted-foreground">
                Maximum number of tokens to generate.
              </p>
            </div>

            {/* Top P */}
            <div className="space-y-2">
              <label className="text-sm font-medium">
                Top P: {settings.topP}
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={settings.topP}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    topP: parseFloat(e.target.value),
                  })
                }
                className="w-full"
              />
              <p className="text-xs text-muted-foreground">
                Nucleus sampling threshold. Lower values limit vocabulary.
              </p>
            </div>

            {/* Advanced Options Collapsible */}
            <div className="border rounded-lg">
              <button
                type="button"
                className="flex items-center justify-between w-full px-4 py-2 text-sm font-medium text-left"
                onClick={() => setAdvancedOpen(!advancedOpen)}
              >
                <span>Advanced Options</span>
                <span className={advancedOpen ? "rotate-180" : ""}>
                  ▼
                </span>
              </button>
              {advancedOpen && (
                <div className="px-4 pb-4 space-y-4">
                  {/* Presence Penalty */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium">
                      Presence Penalty: {settings.presencePenalty}
                    </label>
                    <input
                      type="range"
                      min="-2"
                      max="2"
                      step="0.1"
                      value={settings.presencePenalty}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          presencePenalty: parseFloat(e.target.value),
                        })
                      }
                      className="w-full"
                    />
                    <p className="text-xs text-muted-foreground">
                      Penalize repeat topics. Range: -2 to 2.
                    </p>
                  </div>

                  {/* Frequency Penalty */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium">
                      Frequency Penalty: {settings.frequencyPenalty}
                    </label>
                    <input
                      type="range"
                      min="-2"
                      max="2"
                      step="0.1"
                      value={settings.frequencyPenalty}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          frequencyPenalty: parseFloat(e.target.value),
                        })
                      }
                      className="w-full"
                    />
                    <p className="text-xs text-muted-foreground">
                      Penalize repeat words. Range: -2 to 2.
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* System Prompt */}
            <div className="space-y-2">
              <label className="text-sm font-medium">System Prompt</label>
              <textarea
                value={settings.systemPrompt}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    systemPrompt: e.target.value,
                  })
                }
                className="w-full h-24 p-2 border rounded-md bg-background text-sm resize-none"
                placeholder="You are a helpful AI assistant..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setSettings(defaultSettings);
              }}
            >
              Reset to Defaults
            </Button>
            <Button onClick={() => setSettingsOpen(false)}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Keyboard Shortcuts Dialog */}
      <Dialog open={shortcutsOpen} onOpenChange={setShortcutsOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Keyboard Shortcuts</DialogTitle>
            <DialogDescription>
              Use these shortcuts to speed up your workflow.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2 py-4">
            {keyboardShortcuts.map((shortcut) => (
              <div
                key={shortcut.keys}
                className="flex justify-between items-center"
              >
                <span className="text-sm">{shortcut.action}</span>
                <kbd className="px-2 py-1 bg-secondary rounded text-sm font-mono">
                  {shortcut.keys}
                </kbd>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete Conversation Confirmation Dialog */}
      <Dialog open={deleteConversationConfirmOpen !== null} onOpenChange={(open) => !open && setDeleteConversationConfirmOpen(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Conversation</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this conversation? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConversationConfirmOpen(null)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={confirmDeleteConversation}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Message Confirmation Dialog */}
      <Dialog open={deleteConfirmOpen !== null} onOpenChange={(open) => !open && setDeleteConfirmOpen(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Message</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this message? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirmOpen(null)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={() => deleteConfirmOpen && handleDeleteMessage(deleteConfirmOpen)}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
