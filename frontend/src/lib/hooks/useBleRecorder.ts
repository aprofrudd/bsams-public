import { useState, useRef, useCallback, useEffect } from 'react';
import type { FtmsData } from '../bleProtocol';

export interface BleSample {
  elapsed_ms: number;
  watts: number;
  speed_kmh: number | null;
  cadence_rpm: number | null;
  distance_m: number | null;
  calories_kcal: number | null;
}

type RecorderState = 'idle' | 'countdown' | 'recording' | 'done';

interface UseBleRecorderReturn {
  state: RecorderState;
  samples: BleSample[];
  countdown: number;
  elapsed: number;
  remaining: number;
  start: (durationSec: number) => void;
  stop: () => void;
  reset: () => void;
  handleData: (data: FtmsData) => void;
}

export function useBleRecorder(): UseBleRecorderReturn {
  const [state, setState] = useState<RecorderState>('idle');
  const [samples, setSamples] = useState<BleSample[]>([]);
  const [countdown, setCountdown] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [remaining, setRemaining] = useState(0);

  const stateRef = useRef(state);
  stateRef.current = state;
  const startTimeRef = useRef(0);
  const durationRef = useRef(0);
  const samplesRef = useRef<BleSample[]>([]);
  const rafRef = useRef<number>(0);
  const countdownRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const tick = useCallback(() => {
    if (stateRef.current !== 'recording') return;
    const now = Date.now();
    const elapsedMs = now - startTimeRef.current;
    const elapsedSec = Math.floor(elapsedMs / 1000);
    const remainSec = Math.max(0, durationRef.current - elapsedSec);

    setElapsed(elapsedSec);
    setRemaining(remainSec);

    if (remainSec <= 0) {
      setState('done');
      setSamples([...samplesRef.current]);
      return;
    }
    rafRef.current = requestAnimationFrame(tick);
  }, []);

  const start = useCallback((durationSec: number) => {
    durationRef.current = durationSec;
    samplesRef.current = [];
    setSamples([]);

    // 3-second countdown
    setCountdown(3);
    setState('countdown');
    let count = 3;
    const countdownInterval = setInterval(() => {
      count--;
      if (count <= 0) {
        clearInterval(countdownInterval);
        countdownRef.current = null;
        setCountdown(0);
        startTimeRef.current = Date.now();
        setState('recording');
        setElapsed(0);
        setRemaining(durationSec);
        rafRef.current = requestAnimationFrame(tick);
      } else {
        setCountdown(count);
      }
    }, 1000);
    countdownRef.current = countdownInterval;
  }, [tick]);

  const stop = useCallback(() => {
    if (countdownRef.current) {
      clearInterval(countdownRef.current);
      countdownRef.current = null;
    }
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    setState('done');
    setSamples([...samplesRef.current]);
  }, []);

  const reset = useCallback(() => {
    if (countdownRef.current) clearInterval(countdownRef.current);
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    setState('idle');
    setSamples([]);
    samplesRef.current = [];
    setCountdown(0);
    setElapsed(0);
    setRemaining(0);
  }, []);

  const handleData = useCallback((data: FtmsData) => {
    if (stateRef.current !== 'recording') return;
    const now = Date.now();
    const sample: BleSample = {
      elapsed_ms: now - startTimeRef.current,
      watts: data.instantPower ?? 0,
      speed_kmh: data.instantSpeed ?? null,
      cadence_rpm: data.instantCadence ?? null,
      distance_m: data.totalDistance ?? null,
      calories_kcal: data.totalEnergy ?? null,
    };
    samplesRef.current.push(sample);
  }, []);

  useEffect(() => {
    return () => {
      if (countdownRef.current) clearInterval(countdownRef.current);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  return { state, samples, countdown, elapsed, remaining, start, stop, reset, handleData };
}
