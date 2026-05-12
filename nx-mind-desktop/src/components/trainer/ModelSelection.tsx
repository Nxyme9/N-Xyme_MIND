'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { useModelScanner } from './useTrainer';

export interface ModelInfo {
  id: string;
  name: string;
  size: string;
  parameters: string;
  quantization: string;
  path: string;
}

interface ModelSelectionProps {
  onSelect: (model: ModelInfo) => void;
  selectedModel?: ModelInfo | null;
}

const mockModels: ModelInfo[] = [
  {
    id: 'qwen2.5-0.5b',
    name: 'Qwen 2.5 0.5B',
    size: '400MB',
    parameters: '500M',
    quantization: 'Q4_K_M',
    path: '/models/qwen2.5-0.5b-instruct-q4_k_m.gguf',
  },
  {
    id: 'qwen2.5-1.5b',
    name: 'Qwen 2.5 1.5B',
    size: '1.2GB',
    parameters: '1.5B',
    quantization: 'Q4_K_M',
    path: '/models/qwen2.5-1.5b-instruct-q4_k_m.gguf',
  },
  {
    id: 'qwen2.5-3b',
    name: 'Qwen 2.5 3B',
    size: '2.4GB',
    parameters: '3B',
    quantization: 'Q4_K_M',
    path: '/models/qwen2.5-3b-instruct-q4_k_m.gguf',
  },
  {
    id: 'llama3.2-1b',
    name: 'Llama 3.2 1B',
    size: '1.3GB',
    parameters: '1B',
    quantization: 'Q4_K_M',
    path: '/models/llama3.2-1b-instruct-q4_k_m.gguf',
  },
  {
    id: 'llama3.2-3b',
    name: 'Llama 3.2 3B',
    size: '3.5GB',
    parameters: '3B',
    quantization: 'Q4_K_M',
    path: '/models/llama3.2-3b-instruct-q4_k_m.gguf',
  },
  {
    id: 'qwen2.5-coder-7b',
    name: 'Qwen Coder 7B',
    size: '4.7GB',
    parameters: '7B',
    quantization: 'Q4_K_M',
    path: '/models/qwen2.5-coder-7b-q4_k_m.gguf',
  },
];

export function ModelSelection({ onSelect, selectedModel }: ModelSelectionProps) {
  const { isScanning, models, scanModels } = useModelScanner();
  const [showLocal, setShowLocal] = useState(false);

  useEffect(() => {
    scanModels();
  }, [scanModels]);

  const localModels: ModelInfo[] = models.map(m => ({
    id: m.id,
    name: m.name,
    size: m.size,
    parameters: 'Unknown',
    quantization: 'Q4_K_M',
    path: m.path,
  }));

  const displayModels = showLocal && localModels.length > 0 ? localModels : mockModels;

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 
          className="text-xl font-semibold"
          style={{ color: 'var(--color-text-primary)' }}
        >
          Select Base Model
        </h2>
        <p 
          className="mt-2"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          {showLocal && localModels.length > 0 
            ? `Found ${localModels.length} local model(s)`
            : 'Choose a model to fine-tune. Models must be downloaded first.'}
        </p>
      </div>

      <div className="flex justify-center gap-2">
        <Button 
          variant={!showLocal ? 'primary' : 'secondary'} 
          size="sm"
          onClick={() => setShowLocal(false)}
        >
          Recommended
        </Button>
        <Button 
          variant={showLocal ? 'primary' : 'secondary'} 
          size="sm"
          onClick={() => setShowLocal(true)}
          disabled={isScanning}
        >
          {isScanning ? 'Scanning...' : `Local (${localModels.length})`}
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {displayModels.map((model) => (
          <Card
            key={model.id}
            className={`
              cursor-pointer transition-all duration-200
              hover:scale-[1.02] hover:shadow-lg
              ${selectedModel?.id === model.id 
                ? 'ring-2 ring-[var(--color-accent)]' 
                : ''
              }
            `}
            onClick={() => onSelect(model)}
          >
            <div className="p-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 
                    className="font-semibold text-lg"
                    style={{ color: 'var(--color-text-primary)' }}
                  >
                    {model.name}
                  </h3>
                  <p 
                    className="text-sm mt-1"
                    style={{ color: 'var(--color-text-secondary)' }}
                  >
                    {model.parameters} parameters
                  </p>
                </div>
                {selectedModel?.id === model.id && (
                  <div 
                    className="w-6 h-6 rounded-full flex items-center justify-center"
                    style={{ backgroundColor: 'var(--color-accent)' }}
                  >
                    <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                )}
              </div>

              <div 
                className="mt-4 flex items-center gap-4 text-sm"
                style={{ color: 'var(--color-text-secondary)' }}
              >
                <span className="flex items-center gap-1">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2 1 3 3 3h10c2 0 3-1 3-3V7c0-2-1-3-3-3H7c-2 0-3 1-3 3z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6M12 9v6" />
                  </svg>
                  {model.size}
                </span>
                <span className="px-2 py-0.5 rounded text-xs" style={{ backgroundColor: 'var(--color-bg-tertiary)' }}>
                  {model.quantization}
                </span>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <div className="flex justify-end pt-4">
        <Button
          onClick={() => selectedModel && onSelect(selectedModel)}
          disabled={!selectedModel}
        >
          Continue
        </Button>
      </div>
    </div>
  );
}