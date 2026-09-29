import { useState, useRef, useCallback, useEffect } from 'react';

export interface TimerSetConfig {
  reps: number;
  duration_seconds: number;
  rest_between_reps_seconds: number;
  rest_after_set_seconds: number;
  rep_durations?: number[];
  rest_between_reps?: number[];
  rep_intensity_values?: number[];
}

export interface TimerExercise {
  exercise_name: string;
  sets: TimerSetConfig[];
  intensity_type?: string | null;
  intensity_value?: number | null;
  intensity_min?: number | null;
  intensity_max?: number | null;
}

export type TimerPhase = 'idle' | 'warmup' | 'countdown' | 'work' | 'rest' | 'complete';

export interface TimerState {
  phase: TimerPhase;
  currentExerciseIndex: number;
  currentSet: number;
  currentRep: number;
  timeRemaining: number;
  totalDuration: number;
  isPaused: boolean;
  warmupElapsed: number;
  totalElapsed: number;
}

const COUNTDOWN_SECONDS = 10;

function getRepDuration(set: TimerSetConfig, repNumber: number): number {
  if (set.rep_durations && set.rep_durations.length >= repNumber) {
    return set.rep_durations[repNumber - 1];
  }
  return set.duration_seconds;
}

/** Get rest duration after a specific rep (1-indexed). Uses per-rep array, falls back to scalar. */
function getRestAfterRep(set: TimerSetConfig, repNumber: number): number {
  if (set.rest_between_reps && set.rest_between_reps.length >= repNumber) {
    return set.rest_between_reps[repNumber - 1];
  }
  return set.rest_between_reps_seconds;
}

export function useIntervalTimer(exercises: TimerExercise[]) {
  const [state, setState] = useState<TimerState>({
    phase: 'idle',
    currentExerciseIndex: 0,
    currentSet: 1,
    currentRep: 1,
    timeRemaining: 0,
    totalDuration: 0,
    isPaused: false,
    warmupElapsed: 0,
    totalElapsed: 0,
  });

  const phaseStartTime = useRef<number>(0);
  const phaseDuration = useRef<number>(0);
  const warmupStart = useRef<number>(0);
  const totalStart = useRef<number>(0);
  const pauseOffset = useRef<number>(0);
  const animFrameId = useRef<number>(0);

  // Store state in ref for animation frame access
  const stateRef = useRef(state);
  stateRef.current = state;

  // Store exercises in ref for stable access
  const exercisesRef = useRef(exercises);
  exercisesRef.current = exercises;

  function startPhase(phase: TimerPhase, duration: number, updates: Partial<TimerState> = {}) {
    phaseStartTime.current = Date.now();
    phaseDuration.current = duration;
    pauseOffset.current = 0;
    setState(prev => ({
      ...prev,
      phase,
      timeRemaining: duration,
      totalDuration: duration,
      isPaused: false,
      ...updates,
    }));
    animFrameId.current = requestAnimationFrame(tick);
  }

  function advancePhase() {
    const s = stateRef.current;
    const exs = exercisesRef.current;
    const ex = exs[s.currentExerciseIndex];
    if (!ex) {
      setState(prev => ({ ...prev, phase: 'complete', totalElapsed: Math.floor((Date.now() - totalStart.current - pauseOffset.current) / 1000) }));
      return;
    }

    const currentSetConfig = ex.sets[s.currentSet - 1];

    if (s.phase === 'countdown') {
      const firstSet = ex.sets[0];
      const firstRepDur = getRepDuration(firstSet, 1);
      startPhase('work', firstRepDur, {
        currentSet: 1,
        currentRep: 1,
      });
      return;
    }

    if (s.phase === 'work') {
      // Check if more reps in this set
      if (currentSetConfig && s.currentRep < currentSetConfig.reps) {
        const restDur = getRestAfterRep(currentSetConfig, s.currentRep);
        if (restDur > 0) {
          startPhase('rest', restDur);
          return;
        }
      }
      // Check if more sets
      if (s.currentSet < ex.sets.length) {
        const restDuration = currentSetConfig?.rest_after_set_seconds || 60;
        startPhase('rest', restDuration, {
          currentRep: currentSetConfig?.reps || 1,
        });
        return;
      }
      // Check if more exercises
      if (s.currentExerciseIndex < exs.length - 1) {
        const restDuration = currentSetConfig?.rest_after_set_seconds || 60;
        startPhase('rest', restDuration);
        return;
      }
      // All done
      setState(prev => ({ ...prev, phase: 'complete', totalElapsed: Math.floor((Date.now() - totalStart.current - pauseOffset.current) / 1000) }));
      return;
    }

    if (s.phase === 'rest') {
      // Determine what comes next
      if (currentSetConfig && s.currentRep < currentSetConfig.reps) {
        const nextRep = s.currentRep + 1;
        const nextRepDur = getRepDuration(currentSetConfig, nextRep);
        startPhase('work', nextRepDur, {
          currentRep: nextRep,
        });
        return;
      }
      if (s.currentSet < ex.sets.length) {
        const nextSet = s.currentSet + 1;
        const nextSetConfig = ex.sets[nextSet - 1];
        const nextRepDur = getRepDuration(nextSetConfig, 1);
        startPhase('work', nextRepDur, {
          currentSet: nextSet,
          currentRep: 1,
        });
        return;
      }
      // Next exercise
      const nextIndex = s.currentExerciseIndex + 1;
      if (nextIndex < exs.length) {
        const nextEx = exs[nextIndex];
        const nextSetConfig = nextEx.sets[0];
        const nextRepDur = getRepDuration(nextSetConfig, 1);
        startPhase('work', nextRepDur, {
          currentExerciseIndex: nextIndex,
          currentSet: 1,
          currentRep: 1,
        });
        return;
      }
      // All done
      setState(prev => ({ ...prev, phase: 'complete', totalElapsed: Math.floor((Date.now() - totalStart.current - pauseOffset.current) / 1000) }));
    }
  }

  function tick() {
    const s = stateRef.current;
    if (s.isPaused || s.phase === 'idle' || s.phase === 'complete') return;

    const now = Date.now();

    if (s.phase === 'warmup') {
      const elapsed = Math.floor((now - warmupStart.current - pauseOffset.current) / 1000);
      const totalElapsed = Math.floor((now - totalStart.current - pauseOffset.current) / 1000);
      setState(prev => ({ ...prev, warmupElapsed: elapsed, totalElapsed }));
      animFrameId.current = requestAnimationFrame(tick);
      return;
    }

    const elapsed = (now - phaseStartTime.current - pauseOffset.current) / 1000;
    const remaining = Math.max(0, phaseDuration.current - elapsed);
    const totalElapsed = Math.floor((now - totalStart.current - pauseOffset.current) / 1000);

    if (remaining <= 0) {
      advancePhase();
      return;
    }

    setState(prev => ({ ...prev, timeRemaining: remaining, totalElapsed }));
    animFrameId.current = requestAnimationFrame(tick);
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const start = useCallback(() => {
    const now = Date.now();
    warmupStart.current = now;
    totalStart.current = now;
    pauseOffset.current = 0;
    setState(prev => ({
      ...prev,
      phase: 'warmup',
      warmupElapsed: 0,
      totalElapsed: 0,
      isPaused: false,
    }));
    animFrameId.current = requestAnimationFrame(tick);
  }, []);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const startCountdown = useCallback(() => {
    startPhase('countdown', COUNTDOWN_SECONDS, {
      currentExerciseIndex: 0,
      currentSet: 1,
      currentRep: 1,
    });
  }, []);

  const pauseRef = useRef<number>(0);

  const pause = useCallback(() => {
    pauseRef.current = Date.now();
    cancelAnimationFrame(animFrameId.current);
    setState(prev => ({ ...prev, isPaused: true }));
  }, []);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const resume = useCallback(() => {
    if (pauseRef.current > 0) {
      pauseOffset.current += Date.now() - pauseRef.current;
      pauseRef.current = 0;
    }
    setState(prev => ({ ...prev, isPaused: false }));
    animFrameId.current = requestAnimationFrame(tick);
  }, []);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const skip = useCallback(() => {
    cancelAnimationFrame(animFrameId.current);
    advancePhase();
  }, []);

  const end = useCallback(() => {
    cancelAnimationFrame(animFrameId.current);
    setState(prev => ({ ...prev, phase: 'complete', totalElapsed: Math.floor((Date.now() - totalStart.current - pauseOffset.current) / 1000) }));
  }, []);

  const reset = useCallback(() => {
    cancelAnimationFrame(animFrameId.current);
    setState({
      phase: 'idle',
      currentExerciseIndex: 0,
      currentSet: 1,
      currentRep: 1,
      timeRemaining: 0,
      totalDuration: 0,
      isPaused: false,
      warmupElapsed: 0,
      totalElapsed: 0,
    });
  }, []);

  // Handle visibility change (auto-pause on tab hide)
  useEffect(() => {
    function handleVisibility() {
      if (document.hidden && stateRef.current.phase !== 'idle' && stateRef.current.phase !== 'complete' && !stateRef.current.isPaused) {
        pause();
      }
    }
    document.addEventListener('visibilitychange', handleVisibility);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibility);
      cancelAnimationFrame(animFrameId.current);
    };
  }, [pause]);

  return {
    state,
    start,
    startCountdown,
    pause,
    resume,
    skip,
    end,
    reset,
  };
}
