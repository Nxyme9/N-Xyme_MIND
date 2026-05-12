'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface ModelExportProps {
  onComplete: () => void;
  onBack: () => void;
}

export function ModelExport({ onComplete, onBack }: ModelExportProps) {
  const [isExporting, setIsExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState(0);
  const [exportPath, setExportPath] = useState('~/models/fine-tuned');

  const handleExport = async () => {
    setIsExporting(true);
    for (let i = 0; i <= 100; i += 10) {
      await new Promise(r => setTimeout(r, 300));
      setExportProgress(i);
    }
    setIsExporting(false);
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 
          className="text-xl font-semibold"
          style={{ color: 'var(--color-text-primary)' }}
        >
          Export Fine-Tuned Model
        </h2>
        <p 
          className="mt-2"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          Save your trained model as a GGUF file
        </p>
      </div>

      <Card>
        <div className="p-6 space-y-6">
          <div>
            <label 
              className="block text-sm font-medium mb-2"
              style={{ color: 'var(--color-text-primary)' }}
            >
              Export Path
            </label>
            <input
              type="text"
              value={exportPath}
              onChange={(e) => setExportPath(e.target.value)}
              className="w-full px-4 py-2 rounded-lg border"
              style={{ 
                backgroundColor: 'var(--color-bg-secondary)',
                borderColor: 'var(--color-border)',
                color: 'var(--color-text-primary)',
              }}
            />
          </div>

          <div className="grid grid-cols-2 gap-4 p-4 rounded-lg" style={{ backgroundColor: 'var(--color-bg-secondary)' }}>
            <div>
              <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>Format</p>
              <p className="font-medium" style={{ color: 'var(--color-text-primary)' }}>GGUF (Q4_K_M)</p>
            </div>
            <div>
              <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>Size</p>
              <p className="font-medium" style={{ color: 'var(--color-text-primary)' }}>~500MB</p>
            </div>
          </div>

          {isExporting && (
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span style={{ color: 'var(--color-text-primary)' }}>Exporting...</span>
                <span style={{ color: 'var(--color-text-secondary)' }}>{exportProgress}%</span>
              </div>
              <div 
                className="h-2 rounded-full overflow-hidden"
                style={{ backgroundColor: 'var(--color-bg-tertiary)' }}
              >
                <div 
                  className="h-full transition-all duration-300"
                  style={{ 
                    width: `${exportProgress}%`,
                    backgroundColor: 'var(--color-accent)',
                  }}
                />
              </div>
            </div>
          )}

          <div 
            className="p-4 rounded-lg border"
            style={{ 
              backgroundColor: 'var(--color-success)/10',
              borderColor: 'var(--color-success)',
            }}
          >
            <p className="text-sm" style={{ color: 'var(--color-success)' }}>
              Your fine-tuned model will be saved to: {exportPath}
            </p>
          </div>
        </div>
      </Card>

      <div className="flex justify-between pt-4">
        <Button variant="secondary" onClick={onBack}>
          Back
        </Button>
        <Button 
          onClick={handleExport}
          loading={isExporting}
          disabled={isExporting}
        >
          {isExporting ? 'Exporting...' : 'Export Model'}
        </Button>
      </div>
    </div>
  );
}