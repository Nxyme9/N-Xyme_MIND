'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface TrainingExecutionProps {
  onComplete: () => void;
  onBack: () => void;
}

export interface TrainingStatus {
  phase: 'preparing' | 'training' | 'saving' | 'complete' | 'error';
  currentEpoch: number;
  totalEpochs: number;
  currentStep: number;
  totalSteps: number;
  loss: number;
  learningRate: number;
  elapsedTime: number;
  eta: number;
  error?: string;
}

export function TrainingExecution({ onComplete, onBack }: TrainingExecutionProps) {
  const [status, setStatus] = useState<TrainingStatus>({
    phase: 'preparing',
    currentEpoch: 0,
    totalEpochs: 3,
    currentStep: 0,
    totalSteps: 0,
    loss: 0,
    learningRate: 0,
    elapsedTime: 0,
    eta: 0,
  });

  const [logs, setLogs] = useState<string[]>([]);

  useEffect(() => {
    const interval = setInterval(() => {
      setStatus(prev => {
        if (prev.phase === 'preparing') {
          return { ...prev, phase: 'training', totalSteps: 100 };
        }
        if (prev.phase === 'training') {
          const newStep = prev.currentStep + 1;
          const progress = newStep / prev.totalSteps;
          const newLoss = Math.max(0.1, 2.5 - progress * 2 + Math.random() * 0.1);
          const newLr = prev.learningRate + (2e-5 - prev.learningRate) * 0.01;
          
          setLogs(l => [...l.slice(-50), `[Epoch ${prev.currentEpoch + 1}/${prev.totalEpochs}] Step ${newStep}/${prev.totalSteps} - loss: ${newLoss.toFixed(4)} - lr: ${newLr.toExponential(2)}`]);

          if (newStep >= prev.totalSteps) {
            const newEpoch = prev.currentEpoch + 1;
            if (newEpoch >= prev.totalEpochs) {
              return { ...prev, phase: 'saving', currentStep: newStep };
            }
            return { 
              ...prev, 
              currentEpoch: newEpoch, 
              currentStep: 0,
              totalSteps: 100,
            };
          }
          return { 
            ...prev, 
            currentStep: newStep, 
            loss: newLoss,
            learningRate: newLr,
            elapsedTime: prev.elapsedTime + 1,
          };
        }
        if (prev.phase === 'saving') {
          setLogs(l => [...l.slice(-50), 'Saving model checkpoint...']);
          return { ...prev, phase: 'complete' };
        }
        return prev;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const progressPercent = status.totalSteps > 0 
    ? ((status.currentEpoch * 100 + (status.currentStep / status.totalSteps) * 100) / status.totalEpochs)
    : 0;

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 
          className="text-xl font-semibold"
          style={{ color: 'var(--color-text-primary)' }}
        >
          Training in Progress
        </h2>
        <p 
          className="mt-2"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          {status.phase === 'preparing' && 'Preparing training environment...'}
          {status.phase === 'training' && `Epoch ${status.currentEpoch + 1} of ${status.totalEpochs}`}
          {status.phase === 'saving' && 'Saving model checkpoint...'}
          {status.phase === 'complete' && 'Training complete!'}
          {status.phase === 'error' && `Error: ${status.error}`}
        </p>
      </div>

      <Card>
        <div className="p-6 space-y-6">
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span style={{ color: 'var(--color-text-primary)' }}>Progress</span>
              <span style={{ color: 'var(--color-text-secondary)' }}>
                {Math.round(progressPercent)}%
              </span>
            </div>
            <div 
              className="h-3 rounded-full overflow-hidden"
              style={{ backgroundColor: 'var(--color-bg-tertiary)' }}
            >
              <div 
                className="h-full transition-all duration-300 rounded-full"
                style={{ 
                  width: `${progressPercent}%`,
                  backgroundColor: status.phase === 'complete' ? 'var(--color-success)' : 'var(--color-accent)',
                }}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>Loss</p>
              <p className="text-lg font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                {status.loss.toFixed(4)}
              </p>
            </div>
            <div>
              <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>Learning Rate</p>
              <p className="text-lg font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                {status.learningRate.toExponential(2)}
              </p>
            </div>
            <div>
              <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>Elapsed</p>
              <p className="text-lg font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                {formatTime(status.elapsedTime)}
              </p>
            </div>
            <div>
              <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>ETA</p>
              <p className="text-lg font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                {status.phase === 'complete' ? '--' : formatTime(status.totalEpochs * 100 - status.elapsedTime)}
              </p>
            </div>
          </div>

          <div>
            <p className="text-xs mb-2" style={{ color: 'var(--color-text-secondary)' }}>Training Log</p>
            <div 
              className="h-48 overflow-y-auto p-3 rounded-lg font-mono text-xs"
              style={{ 
                backgroundColor: 'var(--color-bg-tertiary)',
                color: 'var(--color-text-secondary)',
              }}
            >
              {logs.map((log, idx) => (
                <div key={idx}>{log}</div>
              ))}
            </div>
          </div>
        </div>
      </Card>

      <div className="flex justify-between pt-4">
        {status.phase !== 'complete' ? (
          <Button variant="danger" onClick={onBack}>
            Cancel Training
          </Button>
        ) : (
          <div />
        )}
        <Button 
          onClick={onComplete}
          disabled={status.phase !== 'complete' && status.phase !== 'training'}
        >
          {status.phase === 'complete' ? 'Export Model' : 'Training...'}
        </Button>
      </div>
    </div>
  );
}