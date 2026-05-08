import { useState, useEffect, useRef, useCallback } from 'react';

export type CognitiveState = 'surge' | 'drift' | 'dawn';

interface BandwidthIndicators {
  typingSpeed: number;
  pauseDuration: number;
  mouseVelocity: number;
  focusDuration: number;
  errorRate: number;
}

interface CognitiveBandwidthResult {
  state: CognitiveState;
  confidence: number;
  indicators: BandwidthIndicators;
}

const THRESHOLDS = {
  surge: { typingSpeedMin: 200, pauseMax: 200, mouseVelocityMin: 500, focusMax: 3000, errorRateMax: 0.05 },
  drift: { typingSpeedMax: 80, pauseMin: 1500, mouseVelocityMin: 50, focusMin: 8000, errorRateMin: 0.2 },
  dawn: { typingSpeedMin: 100, pauseMax: 800, mouseVelocityMin: 100, focusMax: 5000, errorRateMax: 0.1 },
};

function calculateState(indicators: BandwidthIndicators): { state: CognitiveState; confidence: number } {
  const scores = { surge: 0, drift: 0, dawn: 0 };

  if (indicators.typingSpeed >= THRESHOLDS.surge.typingSpeedMin) scores.surge += 1;
  if (indicators.pauseDuration <= THRESHOLDS.surge.pauseMax) scores.surge += 1;
  if (indicators.mouseVelocity >= THRESHOLDS.surge.mouseVelocityMin) scores.surge += 1;
  if (indicators.focusDuration <= THRESHOLDS.surge.focusMax) scores.surge += 1;
  if (indicators.errorRate <= THRESHOLDS.surge.errorRateMax) scores.surge += 1;

  if (indicators.typingSpeed <= THRESHOLDS.drift.typingSpeedMax) scores.drift += 1;
  if (indicators.pauseDuration >= THRESHOLDS.drift.pauseMin) scores.drift += 1;
  if (indicators.mouseVelocity <= THRESHOLDS.drift.mouseVelocityMin) scores.drift += 1;
  if (indicators.focusDuration >= THRESHOLDS.drift.focusMin) scores.drift += 1;
  if (indicators.errorRate >= THRESHOLDS.drift.errorRateMin) scores.drift += 1;

  if (indicators.typingSpeed >= THRESHOLDS.dawn.typingSpeedMin) scores.dawn += 1;
  if (indicators.pauseDuration <= THRESHOLDS.dawn.pauseMax) scores.dawn += 1;
  if (indicators.mouseVelocity >= THRESHOLDS.dawn.mouseVelocityMin) scores.dawn += 1;
  if (indicators.focusDuration <= THRESHOLDS.dawn.focusMax) scores.dawn += 1;
  if (indicators.errorRate <= THRESHOLDS.dawn.errorRateMax) scores.dawn += 1;

  const maxScore = Math.max(scores.surge, scores.drift, scores.dawn);
  const totalScore = scores.surge + scores.drift + scores.dawn;
  const confidence = totalScore > 0 ? maxScore / totalScore : 0.5;

  if (scores.surge === maxScore) return { state: 'surge', confidence };
  if (scores.drift === maxScore) return { state: 'drift', confidence };
  return { state: 'dawn', confidence };
}

export function useCognitiveBandwidth(pollingInterval = 2000): CognitiveBandwidthResult {
  const [result, setResult] = useState<CognitiveBandwidthResult>({
    state: 'dawn',
    confidence: 0.5,
    indicators: { typingSpeed: 0, pauseDuration: 0, mouseVelocity: 0, focusDuration: 0, errorRate: 0 },
  });

  const keypressTimestamps = useRef<number[]>([]);
  const lastKeypressTime = useRef(0);
  const keypressCount = useRef(0);
  const backspaceCount = useRef(0);
  const mousePositions = useRef<{ x: number; y: number; time: number }[]>([]);
  const focusElementTime = useRef(0);
  const currentElement = useRef<string>('');

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    const now = Date.now();
    if (lastKeypressTime.current > 0) {
      const pause = now - lastKeypressTime.current;
      if (pause > 100) {
        keypressTimestamps.current.push(pause);
        if (keypressTimestamps.current.length > 20) {
          keypressTimestamps.current.shift();
        }
      }
    }
    lastKeypressTime.current = now;
    keypressCount.current += 1;
    if (e.key === 'Backspace') {
      backspaceCount.current += 1;
    }
  }, []);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    const now = Date.now();
    mousePositions.current.push({ x: e.clientX, y: e.clientY, time: now });
    if (mousePositions.current.length > 50) {
      mousePositions.current.shift();
    }
  }, []);

  const handleFocus = useCallback((e: FocusEvent) => {
    if (e.target instanceof HTMLElement) {
      const tag = e.target.tagName.toLowerCase();
      currentElement.current = `${tag}-${e.target.id || e.target.className || 'unknown'}`;
      focusElementTime.current = Date.now();
    }
  }, []);

  const handleBlur = useCallback(() => {
    focusElementTime.current = 0;
    currentElement.current = '';
  }, []);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('focusin', handleFocus);
    document.addEventListener('focusout', handleBlur);

    const interval = setInterval(() => {
      const now = Date.now();
      const timestamps = keypressTimestamps.current;
      const typingSpeed = timestamps.length > 0
        ? Math.round(60000 / (timestamps.reduce((a, b) => a + b, 0) / timestamps.length))
        : 0;
      const pauseDuration = lastKeypressTime.current > 0 ? now - lastKeypressTime.current : 0;

      const positions = mousePositions.current;
      let mouseVelocity = 0;
      if (positions.length >= 2) {
        const recent = positions.slice(-10);
        let totalDistance = 0;
        let totalTime = 0;
        for (let i = 1; i < recent.length; i++) {
          const dx = recent[i].x - recent[i - 1].x;
          const dy = recent[i].y - recent[i - 1].y;
          const dt = recent[i].time - recent[i - 1].time;
          totalDistance += Math.sqrt(dx * dx + dy * dy);
          totalTime += dt;
        }
        mouseVelocity = totalTime > 0 ? Math.round((totalDistance / totalTime) * 1000) : 0;
      }

      const focusDuration = focusElementTime.current > 0 ? now - focusElementTime.current : 0;
      const totalKeys = keypressCount.current;
      const errorRate = totalKeys > 0 ? backspaceCount.current / totalKeys : 0;

      const indicators = { typingSpeed, pauseDuration, mouseVelocity, focusDuration, errorRate };
      const { state, confidence } = calculateState(indicators);

      setResult({ state, confidence, indicators });
    }, pollingInterval);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('focusin', handleFocus);
      document.removeEventListener('focusout', handleBlur);
      clearInterval(interval);
    };
  }, [handleKeyDown, handleMouseMove, handleFocus, handleBlur, pollingInterval]);

  return result;
}