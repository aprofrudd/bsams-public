import { useRef, useCallback } from 'react';

export function useTimerAudio() {
  const audioCtxRef = useRef<AudioContext | null>(null);

  const getContext = useCallback(() => {
    if (!audioCtxRef.current) {
      audioCtxRef.current = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
    }
    return audioCtxRef.current;
  }, []);

  const playBeep = useCallback((frequency: number, durationMs: number) => {
    try {
      const ctx = getContext();
      const oscillator = ctx.createOscillator();
      const gainNode = ctx.createGain();
      oscillator.connect(gainNode);
      gainNode.connect(ctx.destination);
      oscillator.frequency.value = frequency;
      gainNode.gain.value = 0.3;
      oscillator.start();
      oscillator.stop(ctx.currentTime + durationMs / 1000);
    } catch {
      // Audio not available — silent fallback
    }
  }, [getContext]);

  const playCountdownBeep = useCallback(() => {
    playBeep(800, 200);
  }, [playBeep]);

  const playTransitionBeep = useCallback(() => {
    playBeep(1000, 500);
  }, [playBeep]);

  const initAudio = useCallback(() => {
    // Call on first user interaction to satisfy browser autoplay policy
    getContext();
  }, [getContext]);

  const playGoBeep = useCallback(() => {
    playBeep(1200, 250);
  }, [playBeep]);

  const playStopBeep = useCallback(() => {
    playBeep(400, 300);
  }, [playBeep]);

  return { playCountdownBeep, playTransitionBeep, playGoBeep, playStopBeep, initAudio };
}
