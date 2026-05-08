"use client";

import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";

export type ProviderType = "openrouter" | "gguf" | "free";

interface Model {
  id: string;
  name: string;
  provider: ProviderType;
  description?: string;
}

const AVAILABLE_MODELS: Model[] = [
  { id: "minimax-m2.5-free", name: "Minimax M2.5 Free", provider: "free", description: "Fast, free tier" },
  { id: "qwen3.6-plus-free", name: "Qwen 3.6 Plus Free", provider: "free", description: "Open source free" },
  { id: "kimi-k2.5-free", name: "Kimi K2.5 Free", provider: "free", description: "Chinese LLM" },
  { id: "openrouter/openai/gpt-4o", name: "GPT-4o", provider: "openrouter", description: "OpenAI flagship" },
  { id: "openrouter/openai/gpt-4o-mini", name: "GPT-4o Mini", provider: "openrouter", description: "OpenAI fast" },
  { id: "openrouter/anthropic/claude-3.5-sonnet", name: "Claude 3.5 Sonnet", provider: "openrouter", description: "Anthropic balanced" },
  { id: "openrouter/anthropic/claude-3-haiku", name: "Claude 3 Haiku", provider: "openrouter", description: "Anthropic fast" },
  { id: "openrouter/google/gemini-1.5-pro", name: "Gemini 1.5 Pro", provider: "openrouter", description: "Google multimodal" },
  { id: "openrouter/google/gemini-2.0-flash", name: "Gemini 2.0 Flash", provider: "openrouter", description: "Google fast" },
  { id: "gguf/qwen2.5-coder-7b", name: "Qwen2.5 Coder 7B", provider: "gguf", description: "Local coding" },
  { id: "gguf/llama3.2-3b", name: "Llama 3.2 3B", provider: "gguf", description: "Local general" },
];

interface UnifiedProviderSelectorProps {
  className?: string;
  selectedModel?: string;
  onModelChange?: (modelId: string) => void;
}

export function UnifiedProviderSelector({ className, selectedModel, onModelChange }: UnifiedProviderSelectorProps) {
  const [activeTab, setActiveTab] = useState<ProviderType>("free");
  const [selected, setSelected] = useState(selectedModel || "minimax-m2.5-free");

  const filteredModels = AVAILABLE_MODELS.filter((m) => m.provider === activeTab);

  const handleSelect = (modelId: string) => {
    setSelected(modelId);
    onModelChange?.(modelId);
  };

  const tabStyles = (tab: ProviderType) =>
    cn(
      "px-4 py-2 rounded-lg text-sm font-medium transition-colors",
      activeTab === tab
        ? "bg-primary text-primary-foreground"
        : "bg-muted text-muted-foreground hover:text-foreground"
    );

  return (
    <div className={cn("space-y-4", className)}>
      <div className="flex items-center gap-2">
        <button onClick={() => setActiveTab("free")} className={tabStyles("free")}>
          Free
        </button>
        <button onClick={() => setActiveTab("openrouter")} className={tabStyles("openrouter")}>
          OpenRouter
        </button>
        <button onClick={() => setActiveTab("gguf")} className={tabStyles("gguf")}>
          GGUF Local
        </button>
      </div>

      <div className="grid grid-cols-1 gap-2">
        {filteredModels.map((model) => (
          <button
            key={model.id}
            onClick={() => handleSelect(model.id)}
            className={cn(
              "flex items-center justify-between p-3 rounded-lg border text-left transition-all",
              selected === model.id
                ? "border-primary bg-primary/10"
                : "border-border bg-card hover:border-primary/50"
            )}
          >
            <div>
              <div className="font-medium text-sm">{model.name}</div>
              {model.description && (
                <div className="text-xs text-muted-foreground">{model.description}</div>
              )}
            </div>
            {selected === model.id && (
              <span className="w-2 h-2 rounded-full bg-primary" />
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

export function getAvailableModels() {
  return AVAILABLE_MODELS;
}

export function getModelsByProvider(provider: ProviderType) {
  return AVAILABLE_MODELS.filter((m) => m.provider === provider);
}