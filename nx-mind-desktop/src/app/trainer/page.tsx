'use client';

import { useState } from 'react';
import { Sidebar } from '@/components/shared/Sidebar';
import { StepIndicator } from '@/components/ui/StepIndicator';
import { Card } from '@/components/ui/Card';
import { DataUpload } from '@/components/trainer/DataUpload';
import { ModelSelection, type ModelInfo } from '@/components/trainer/ModelSelection';
import { TrainingConfig, type TrainingConfigData } from '@/components/trainer/TrainingConfig';
import { TrainingExecution } from '@/components/trainer/TrainingExecution';
import { ModelExport } from '@/components/trainer/ModelExport';

interface WizardState {
  data: { rows: Record<string, string>[]; columns: string[]; totalRows: number; filename: string } | null;
  model: ModelInfo | null;
  config: TrainingConfigData | null;
}

const steps = [
  { id: 1, label: 'Data' },
  { id: 2, label: 'Model' },
  { id: 3, label: 'Config' },
  { id: 4, label: 'Train' },
  { id: 5, label: 'Export' },
];

export default function TrainerPage() {
  const [currentStep, setCurrentStep] = useState(1);
  const [wizardState, setWizardState] = useState<WizardState>({
    data: null,
    model: null,
    config: null,
  });

  const handleDataComplete = (data: WizardState['data']) => {
    setWizardState(prev => ({ ...prev, data }));
    setCurrentStep(2);
  };

  const handleModelSelect = (model: ModelInfo) => {
    setWizardState(prev => ({ ...prev, model }));
    setCurrentStep(3);
  };

  const handleConfigComplete = (config: TrainingConfigData) => {
    setWizardState(prev => ({ ...prev, config }));
    setCurrentStep(4);
  };

  const getTrainingConfig = () => {
    if (!wizardState.data || !wizardState.model || !wizardState.config) return null;
    return {
      model_id: wizardState.model.path,
      data_path: 'uploaded_data.jsonl',
      epochs: wizardState.config.epochs,
      batch_size: wizardState.config.batchSize,
      learning_rate: wizardState.config.learningRate,
    };
  };

  const handleTrainingComplete = () => {
    setCurrentStep(5);
  };

  const handleBack = () => {
    setCurrentStep(prev => Math.max(1, prev - 1));
  };

  const renderStep = () => {
    switch (currentStep) {
      case 1:
        return <DataUpload onComplete={handleDataComplete} />;
      case 2:
        return (
          <ModelSelection
            onSelect={handleModelSelect}
            selectedModel={wizardState.model}
          />
        );
      case 3:
        return <TrainingConfig onComplete={handleConfigComplete} onBack={handleBack} />;
      case 4:
        return (
          <TrainingExecution 
            config={getTrainingConfig()!} 
            onComplete={handleTrainingComplete} 
            onBack={handleBack} 
          />
        );
      case 5:
        return <ModelExport onComplete={() => alert('Done!')} onBack={handleBack} />;
      default:
        return null;
    }
  };

  return (
    <div className="flex h-screen">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        <header 
          className="h-16 border-b flex items-center justify-between px-6"
          style={{ borderColor: 'var(--color-border)' }}
        >
          <h1 
            className="text-xl font-semibold"
            style={{ color: 'var(--color-text-primary)' }}
          >
            Train Your Model
          </h1>
          <StepIndicator 
            steps={steps} 
            currentStep={currentStep} 
            onStepClick={setCurrentStep}
          />
        </header>

        <div className="flex-1 overflow-auto p-6">
          <Card className="max-w-4xl mx-auto">
            {renderStep()}
          </Card>
        </div>
      </main>
    </div>
  );
}