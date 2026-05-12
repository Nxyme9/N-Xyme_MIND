'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

interface TrainingConfigProps {
  onComplete: (config: TrainingConfigData) => void;
  onBack: () => void;
}

export interface TrainingConfigData {
  epochs: number;
  batchSize: number;
  learningRate: number;
  contextLength: number;
  warmupRatio: number;
}

export function TrainingConfig({ onComplete, onBack }: TrainingConfigProps) {
  const [config, setConfig] = useState<TrainingConfigData>({
    epochs: 3,
    batchSize: 4,
    learningRate: 2e-5,
    contextLength: 2048,
    warmupRatio: 0.1,
  });

  const handleSubmit = () => {
    onComplete(config);
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 
          className="text-xl font-semibold"
          style={{ color: 'var(--color-text-primary)' }}
        >
          Training Configuration
        </h2>
        <p 
          className="mt-2"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          Configure hyperparameters for fine-tuning
        </p>
      </div>

      <Card>
        <div className="p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label 
                className="block text-sm font-medium mb-2"
                style={{ color: 'var(--color-text-primary)' }}
              >
                Epochs
              </label>
              <Input
                type="number"
                min={1}
                max={100}
                value={config.epochs}
                onChange={(e) => setConfig(prev => ({ ...prev, epochs: parseInt(e.target.value) || 1 }))}
              />
              <p 
                className="mt-1 text-xs"
                style={{ color: 'var(--color-text-secondary)' }}
              >
                Number of training passes over the data
              </p>
            </div>

            <div>
              <label 
                className="block text-sm font-medium mb-2"
                style={{ color: 'var(--color-text-primary)' }}
              >
                Batch Size
              </label>
              <Input
                type="number"
                min={1}
                max={64}
                value={config.batchSize}
                onChange={(e) => setConfig(prev => ({ ...prev, batchSize: parseInt(e.target.value) || 1 }))}
              />
              <p 
                className="mt-1 text-xs"
                style={{ color: 'var(--color-text-secondary)' }}
              >
                Samples processed per training step
              </p>
            </div>

            <div>
              <label 
                className="block text-sm font-medium mb-2"
                style={{ color: 'var(--color-text-primary)' }}
              >
                Learning Rate
              </label>
              <Input
                type="number"
                step={1e-6}
                min={1e-6}
                max={1e-3}
                value={config.learningRate}
                onChange={(e) => setConfig(prev => ({ ...prev, learningRate: parseFloat(e.target.value) || 2e-5 }))}
              />
              <p 
                className="mt-1 text-xs"
                style={{ color: 'var(--color-text-secondary)' }}
              >
                Step size for gradient updates
              </p>
            </div>

            <div>
              <label 
                className="block text-sm font-medium mb-2"
                style={{ color: 'var(--color-text-primary)' }}
              >
                Context Length
              </label>
              <Input
                type="number"
                min={512}
                max={8192}
                step={512}
                value={config.contextLength}
                onChange={(e) => setConfig(prev => ({ ...prev, contextLength: parseInt(e.target.value) || 2048 }))}
              />
              <p 
                className="mt-1 text-xs"
                style={{ color: 'var(--color-text-secondary)' }}
              >
                Maximum sequence length in tokens
              </p>
            </div>

            <div className="md:col-span-2">
              <label 
                className="block text-sm font-medium mb-2"
                style={{ color: 'var(--color-text-primary)' }}
              >
                Warmup Ratio: {config.warmupRatio * 100}%
              </label>
              <input
                type="range"
                min={0}
                max={0.5}
                step={0.05}
                value={config.warmupRatio}
                onChange={(e) => setConfig(prev => ({ ...prev, warmupRatio: parseFloat(e.target.value) }))}
                className="w-full h-2 rounded-lg appearance-none cursor-pointer"
                style={{ accentColor: 'var(--color-accent)' }}
              />
              <p 
                className="mt-1 text-xs"
                style={{ color: 'var(--color-text-secondary)' }}
              >
                Percentage of training for learning rate warmup
              </p>
            </div>
          </div>
        </div>
      </Card>

      <div className="flex justify-between pt-4">
        <Button variant="secondary" onClick={onBack}>
          Back
        </Button>
        <Button onClick={handleSubmit}>
          Start Training
        </Button>
      </div>
    </div>
  );
}