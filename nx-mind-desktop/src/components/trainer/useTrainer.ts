'use client';

import { useState, useCallback } from 'react';

export interface TrainingConfig {
  model_id: string;
  data_path: string;
  task_type: string;
  epochs: number;
  learning_rate: number;
  batch_size: number;
}

export interface Job {
  id: string;
  created_at: string;
  updated_at: string;
  status: string;
  model_id: string;
  data_path: string;
  task_type: string;
  epochs: number;
  learning_rate: number;
  batch_size: number;
  current_epoch: number;
  loss_history: string | null;
  final_loss: number | null;
  gguf_path: string | null;
  error_message: string | null;
}

export interface GPUInfo {
  name: string;
  memory_total: number;
  memory_used: number;
  memory_free: number;
  utilization: number;
}

declare global {
  interface Window {
    __TAURI__?: {
      invoke: <T>(cmd: string, args?: Record<string, unknown>) => Promise<T>;
    };
  }
}

async function invoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  if (window.__TAURI__) {
    return window.__TAURI__.invoke<T>(cmd, args);
  }
  throw new Error('Tauri not available');
}

export function useTrainer() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentJob, setCurrentJob] = useState<Job | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [gpuInfo, setGpuInfo] = useState<GPUInfo | null>(null);

  const initDatabase = useCallback(async () => {
    try {
      setIsLoading(true);
      await invoke('init_database');
    } catch (err) {
      console.error('Failed to init database:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const createJob = useCallback(async (config: TrainingConfig): Promise<Job> => {
    setIsLoading(true);
    setError(null);
    try {
      const job = await invoke<Job>('create_training_job', { config });
      setCurrentJob(job);
      return job;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to create job';
      setError(msg);
      throw new Error(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const getJobStatus = useCallback(async (jobId: string): Promise<Job> => {
    const job = await invoke<Job>('get_job_status', { jobId });
    setCurrentJob(job);
    return job;
  }, []);

  const startTraining = useCallback(async (jobId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await invoke('start_training', { jobId });
      await getJobStatus(jobId);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to start training';
      setError(msg);
      throw new Error(msg);
    } finally {
      setIsLoading(false);
    }
  }, [getJobStatus]);

  const cancelTraining = useCallback(async (jobId: string) => {
    setIsLoading(true);
    try {
      await invoke('cancel_training', { jobId });
      await getJobStatus(jobId);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to cancel training';
      setError(msg);
      throw new Error(msg);
    } finally {
      setIsLoading(false);
    }
  }, [getJobStatus]);

  const listJobs = useCallback(async () => {
    const result = await invoke<Job[]>('list_training_jobs');
    setJobs(result);
    return result;
  }, []);

  const fetchGpuInfo = useCallback(async () => {
    try {
      const info = await invoke<GPUInfo>('get_gpu_info');
      setGpuInfo(info);
      return info;
    } catch (err) {
      console.error('Failed to get GPU info:', err);
      return null;
    }
  }, []);

  const hasGpu = useCallback(async (): Promise<boolean> => {
    try {
      return await invoke<boolean>('has_gpu');
    } catch {
      return false;
    }
  }, []);

  return {
    isLoading,
    error,
    currentJob,
    jobs,
    gpuInfo,
    initDatabase,
    createJob,
    getJobStatus,
    startTraining,
    cancelTraining,
    listJobs,
    fetchGpuInfo,
    hasGpu,
  };
}

export function useModelScanner() {
  const [isScanning, setIsScanning] = useState(false);
  const [models, setModels] = useState<{ id: string; name: string; path: string; size: string }[]>([]);

  const scanModels = useCallback(async () => {
    setIsScanning(true);
    try {
      const foundModels = await invoke<{ id: string; name: string; path: string; size: string }[]>('scan_model_files');
      setModels(foundModels);
      return foundModels;
    } catch (err) {
      console.error('Failed to scan models:', err);
      return [];
    } finally {
      setIsScanning(false);
    }
  }, []);

  return { isScanning, models, scanModels };
}