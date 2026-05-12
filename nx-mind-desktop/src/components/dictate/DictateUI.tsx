import { useState, useEffect, useCallback } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { VoiceCommandBadge } from '@/components/ui/badge';
import { Clock } from 'lucide-react';
import { useToast } from '@/context/ToastContext';
import { Toaster } from '@/components/ui/toaster';

interface DictationState {
  status: 'idle' | 'recording' | 'processing' | 'completed' | 'error';
  transcript: string;
  confidence: number;
  duration: number;
  error?: string;
}

export const DictateUI = () => {
  const { addToast } = useToast();
  const [state, setState] = useState<DictationState>({
    status: 'idle',
    transcript: '',
    confidence: 0,
    duration: 0,
  });

  const [isListening, setIsListening] = useState(false);
  const [volumeLevel, setVolumeLevel] = useState(0);

  useEffect(() => {
    if (state.status === 'recording') {
      const interval = setInterval(() => {
        setVolumeLevel(Math.random() * 100);
      }, 100);
      
      return () => clearInterval(interval);
    } else {
      setVolumeLevel(0);
    }
  }, [state.status]);

  useEffect(() => {
    if (state.status === 'completed') {
      const timer = setTimeout(() => {
        setState(prev => ({
          ...prev,
          status: 'idle',
          transcript: '',
          confidence: 0,
          duration: 0,
        }));
      }, 5000);
      
      return () => clearTimeout(timer);
    }
  }, [state.status]);

  const startRecording = useCallback(async () => {
    try {
      setState({
        status: 'recording',
        transcript: '',
        confidence: 0,
        duration: 0,
      });

      const response = await fetch('/api/dictate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'start' }),
      });

      if (response.ok) {
        const result = await response.json();
        
        const pollInterval = setInterval(async () => {
          const statusRes = await fetch('/api/dictate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'status' }),
          });
          
          if (statusRes.ok) {
            const status = await statusRes.json();
            
            if (status.live_partial) {
              setState(prev => ({
                ...prev,
                status: 'recording',
                transcript: status.live_partial,
              }));
            }
            
            if (status.last_result && status.last_result.text) {
              clearInterval(pollInterval);
              setState({
                status: 'completed',
                transcript: status.last_result.text,
                confidence: 0.92,
                duration: 2.5,
              });
              addToast("Dictation complete!", "success");
            }
          }
        }, 300);
        
        (window as any).__pollInterval = pollInterval;
      } else {
        throw new Error('Dictation service unavailable');
      }
    } catch (error) {
      setState({
        status: 'error',
        transcript: '',
        confidence: 0,
        duration: 0,
        error: 'Failed to connect to dictation service'
      });
      
      addToast("Dictation service unavailable. Make sure nxyme-dictate is running.", "error");
    }
  }, []);

  const resetDictation = useCallback(() => {
    const pollInterval = (window as any).__pollInterval;
    if (pollInterval) {
      clearInterval(pollInterval);
      (window as any).__pollInterval = null;
    }
    
    fetch('/api/dictate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'stop' }),
    }).catch(() => {});
    
    setState({
      status: 'idle',
      transcript: '',
      confidence: 0,
      duration: 0,
    });
    
    setIsListening(false);
    setVolumeLevel(0);
  }, []);

  const getStateConfig = () => {
    switch (state.status) {
      case 'idle':
        return {
          color: 'border-muted',
          bg: 'bg-muted/50',
          icon: '🎤',
          label: 'Ready to Record',
          pulse: false
        };
      case 'recording':
        return {
          color: 'border-destructive',
          bg: 'bg-destructive/50',
          icon: '⏺',
          label: 'Listening...',
          pulse: true
        };
      case 'processing':
        return {
          color: 'border-warning',
          bg: 'bg-warning/50',
          icon: '⚡',
          label: 'Processing...',
          pulse: true
        };
      case 'completed':
        return {
          color: 'border-success',
          bg: 'bg-success/50',
          icon: '✓',
          label: 'Complete!',
          pulse: false
        };
      case 'error':
        return {
          color: 'border-destructive',
          bg: 'bg-destructive/50',
          icon: '✕',
          label: 'Error',
          pulse: false
        };
      default:
        return {
          color: 'border-muted',
          bg: 'bg-muted/50',
          icon: '🎤',
          label: 'Ready to Record',
          pulse: false
        };
    }
  };

  const { color, bg, icon, label, pulse } = getStateConfig();

  return (
    <div className="space-y-4">
      <Toaster />
      
      <Card className="transition-all duration-300">
        <CardHeader className="flex items-center justify-between p-4">
          <div className="flex items-center space-x-3">
            <div className={`w-10 h-10 flex items-center justify-center rounded-full ${color} ${bg} ${pulse ? 'animate-pulse' : ''}`}>
              {icon}
            </div>
            <div>
              <CardTitle className="text-lg font-semibold">{label}</CardTitle>
              {state.status === 'recording' && (
                <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                  <div className="h-2 w-2 bg-destructive rounded-full animate-pulse"></div>
                  <span>Capturing audio...</span>
                </div>
              )}
              {state.status === 'processing' && (
                <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                  <div className="h-2 w-2 bg-warning rounded-full animate-pulse"></div>
                  <span>Transcribing...</span>
                </div>
              )}
            </div>
          </div>
          
          <div className="flex items-center space-x-3 text-sm">
            {state.status === 'completed' && (
              <Badge variant="secondary">
                Confidence: {(state.confidence * 100).toFixed(0)}%
              </Badge>
            )}
            {state.status !== 'idle' && state.duration > 0 && (
              <Badge variant="secondary">
                Duration: {state.duration.toFixed(1)}s
              </Badge>
            )}
          </div>
        </CardHeader>
        
        <CardContent className="p-4">
          {state.status === 'idle' && (
            <div className="text-center py-8">
              <VoiceCommandBadge 
                className="mb-4"
                label="Hold hotkey to record"
                variant="outline"
              />
              <p className="text-muted-foreground max-w-md mx-auto">
                Press and hold your dictation hotkey to begin recording.
                Release to process your voice input.
              </p>
            </div>
          )}
          
          {state.transcript && (
            <div className="mt-4 p-4 bg-muted/50 rounded-lg border border-muted">
              {state.status === 'processing' && (
                <div className="mb-2">
                  <span className="text-xs text-muted-foreground animate-pulse">
                    Transcribing...
                  </span>
                </div>
              )}
              <p className="whitespace-pre-wrap break-words text-sm">
                {state.transcript}
              </p>
              {state.status === 'completed' && (
                <div className="mt-2 flex justify-end">
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={() => {
                      navigator.clipboard.writeText(state.transcript);
                      addToast("Copied to clipboard!", "success");
                    }}
                  >
                    Copy Text
                  </Button>
                </div>
              )}
            </div>
          )}
          
          {state.status === 'recording' && (
            <div className="mt-4">
              <div className="flex items-center space-x-2 mb-2">
                <span className="text-sm text-muted-foreground">Input Level:</span>
                <div className="flex-1 bg-muted/50 h-2 rounded-full overflow-hidden">
                  <div 
                    className={`h-full w-${volumeLevel}% bg-${state.status === 'recording' ? 'success' : 'muted'} transition-all duration-100`}
                  ></div>
                </div>
                <span className="text-sm text-muted-foreground">{volumeLevel.toFixed(0)}%</span>
              </div>
              
              {volumeLevel > 70 && (
                <div className="mt-2 text-center text-sm">
                  <span className="text-success">🔥 Strong Signal!</span>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
      
      <div className="flex justify-center space-x-3">
        {state.status === 'idle' && (
          <Button 
            variant="outline" 
            onClick={startRecording}
            className="flex items-center space-x-2 px-6 py-3"
          >
            <span className="mr-2">🎤</span>
            Start Dictation
          </Button>
        )}
        
        {(state.status === 'recording' || state.status === 'processing') && (
          <Button 
            variant="destructive" 
            onClick={resetDictation}
            className="flex items-center space-x-2 px-6 py-3"
          >
            <span className="mr-2">✕</span>
            Cancel
          </Button>
        )}
        
        {state.status === 'completed' && (
          <>
            <Button 
              variant="secondary" 
              onClick={() => {
                navigator.clipboard.writeText(state.transcript);
                addToast("Copied to clipboard!", "success");
              }}
              className="flex items-center space-x-2 px-6 py-3"
            >
              <span className="mr-2">📋</span>
              Copy to Clipboard
            </Button>
            
            <Button 
              variant="outline" 
              onClick={resetDictation}
              className="flex items-center space-x-2 px-6 py-3"
            >
              <span className="mr-2">🔄</span>
              New Dictation
            </Button>
          </>
        )}
        
        {state.status === 'error' && (
          <Button 
            variant="outline" 
            onClick={resetDictation}
            className="flex items-center space-x-2 px-6 py-3"
          >
            <span className="mr-2">🔄</span>
            Try Again
          </Button>
        )}
      </div>
    </div>
  );
};

export default DictateUI;