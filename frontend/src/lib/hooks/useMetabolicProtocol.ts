'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import type { PowerSample } from '../metabolicEngine';

export type MetabolicPhase =
  | 'INACTIVE'
  | 'SETUP'
  | 'WARMUP'
  | 'COUNTDOWN_1' | 'SPRINT_1' | 'REST_1'
  | 'COUNTDOWN_2' | 'SPRINT_2' | 'REST_2'
  | 'COUNTDOWN_3' | 'SPRINT_3'
  | 'POST_TEST'
  | 'RESULTS'
  | 'SPRINT_ENTRY';

export interface MetabolicConfig {
  bodyMassKg: number;
  restingLactate: number;
  dataSource: 'ble' | 'manual';
}

export interface MetabolicProtocolState {
  phase: MetabolicPhase;
  config: MetabolicConfig | null;
  countdown: number;
  sprintRemaining: number;
  restRemaining: number;
  restTotal: number;
  currentSprintNum: number;
  sprint1Samples: PowerSample[];
  sprint2Samples: PowerSample[];
  sprint3Samples: PowerSample[];
  laPeak1: number | null;
  laPeak2: number | null;
  laPeak3: number | null;
  postTestRemaining: number;
}

interface UseMetabolicProtocolReturn {
  state: MetabolicProtocolState;
  beginProtocol: (config: MetabolicConfig) => void;
  startProtocol: () => void;
  submitLactate: (value: number) => void;
  submitManualEntry: (powers: [number, number, number], lactates: [number, number, number]) => void;
  submitFinalLactate: (value: number) => void;
  handlePowerSample: (watts: number) => void;
  goToResults: () => void;
  reset: () => void;
}

const SPRINT_DURATIONS = [10, 20, 30]; // seconds per sprint
const REST_DURATIONS = [6 * 60, 15 * 60]; // seconds per rest (360, 900)
const COUNTDOWN_SECONDS = 5;
const POST_TEST_SECONDS = 3 * 60; // 180 seconds

function initialState(): MetabolicProtocolState {
  return {
    phase: 'INACTIVE',
    config: null,
    countdown: 0,
    sprintRemaining: 0,
    restRemaining: 0,
    restTotal: 0,
    currentSprintNum: 0,
    sprint1Samples: [],
    sprint2Samples: [],
    sprint3Samples: [],
    laPeak1: null,
    laPeak2: null,
    laPeak3: null,
    postTestRemaining: 0,
  };
}

export function useMetabolicProtocol(): UseMetabolicProtocolReturn {
  const [state, setState] = useState<MetabolicProtocolState>(initialState());
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const sprintStartRef = useRef(0);
  const phaseRef = useRef(state.phase);
  phaseRef.current = state.phase;

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const startCountdown = useCallback((sprintNum: 1 | 2 | 3) => {
    clearTimer();
    const countdownPhase = `COUNTDOWN_${sprintNum}` as MetabolicPhase;
    const sprintPhase = `SPRINT_${sprintNum}` as MetabolicPhase;

    setState(prev => ({ ...prev, phase: countdownPhase, countdown: COUNTDOWN_SECONDS, currentSprintNum: sprintNum }));

    let remaining = COUNTDOWN_SECONDS;
    timerRef.current = setInterval(() => {
      remaining--;
      if (remaining <= 0) {
        clearTimer();
        // Start sprint
        sprintStartRef.current = Date.now();
        const sprintDuration = SPRINT_DURATIONS[sprintNum - 1];
        setState(prev => ({
          ...prev,
          phase: sprintPhase,
          countdown: 0,
          sprintRemaining: sprintDuration,
          currentSprintNum: sprintNum,
        }));
        startSprintTimer(sprintNum, sprintDuration);
      } else {
        setState(prev => ({ ...prev, countdown: remaining }));
      }
    }, 1000);
  }, [clearTimer]);

  const startSprintTimer = useCallback((sprintNum: number, durationSec: number) => {
    clearTimer();
    let remaining = durationSec;
    timerRef.current = setInterval(() => {
      remaining--;
      if (remaining <= 0) {
        clearTimer();
        setState(prev => ({ ...prev, sprintRemaining: 0, currentSprintNum: 0 }));

        // Transition to next phase
        if (sprintNum === 1) {
          startRest(1);
        } else if (sprintNum === 2) {
          startRest(2);
        } else {
          // After sprint 3, go to post-test
          startPostTest();
        }
      } else {
        setState(prev => ({ ...prev, sprintRemaining: remaining }));
      }
    }, 1000);
  }, [clearTimer]);

  const startRest = useCallback((restNum: 1 | 2) => {
    clearTimer();
    const restDuration = REST_DURATIONS[restNum - 1];
    const restPhase = `REST_${restNum}` as MetabolicPhase;

    setState(prev => ({
      ...prev,
      phase: restPhase,
      restRemaining: restDuration,
      restTotal: restDuration,
    }));

    let remaining = restDuration;
    timerRef.current = setInterval(() => {
      remaining--;
      if (remaining <= 0) {
        clearTimer();
        setState(prev => ({ ...prev, restRemaining: 0 }));
        // Don't auto-advance — wait for lactate input
      } else {
        setState(prev => ({ ...prev, restRemaining: remaining }));
      }
    }, 1000);
  }, [clearTimer]);

  const startPostTest = useCallback(() => {
    clearTimer();
    setState(prev => ({
      ...prev,
      phase: 'POST_TEST',
      postTestRemaining: POST_TEST_SECONDS,
    }));

    let remaining = POST_TEST_SECONDS;
    timerRef.current = setInterval(() => {
      remaining--;
      if (remaining <= 0) {
        clearTimer();
        setState(prev => ({ ...prev, postTestRemaining: 0 }));
      } else {
        setState(prev => ({ ...prev, postTestRemaining: remaining }));
      }
    }, 1000);
  }, [clearTimer]);

  const beginProtocol = useCallback((config: MetabolicConfig) => {
    setState({
      ...initialState(),
      phase: 'WARMUP',
      config,
    });
  }, []);

  const startProtocol = useCallback(() => {
    setState(prev => {
      if (prev.config?.dataSource === 'manual') {
        return { ...prev, phase: 'SPRINT_ENTRY' };
      }
      return prev;
    });
    // For BLE mode, start countdown 1
    if (state.config?.dataSource !== 'manual') {
      startCountdown(1);
    }
  }, [state.config, startCountdown]);

  const submitLactate = useCallback((value: number) => {
    setState(prev => {
      if (prev.phase === 'REST_1') {
        return { ...prev, laPeak1: value };
      } else if (prev.phase === 'REST_2') {
        return { ...prev, laPeak2: value };
      }
      return prev;
    });

    // Advance after state update
    clearTimer();
    if (phaseRef.current === 'REST_1') {
      setState(prev => ({ ...prev, laPeak1: value }));
      startCountdown(2);
    } else if (phaseRef.current === 'REST_2') {
      setState(prev => ({ ...prev, laPeak2: value }));
      startCountdown(3);
    }
  }, [clearTimer, startCountdown]);

  const submitManualEntry = useCallback((
    powers: [number, number, number],
    lactates: [number, number, number]
  ) => {
    setState(prev => ({
      ...prev,
      phase: 'RESULTS',
      laPeak1: lactates[0],
      laPeak2: lactates[1],
      laPeak3: lactates[2],
      // Store avg power as single-sample equivalents for manual mode
      sprint1Samples: [{ elapsed_ms: 5000, watts: powers[0] }],
      sprint2Samples: [{ elapsed_ms: 15000, watts: powers[1] }],
      sprint3Samples: [{ elapsed_ms: 25000, watts: powers[2] }],
    }));
  }, []);

  const submitFinalLactate = useCallback((value: number) => {
    clearTimer();
    setState(prev => ({
      ...prev,
      phase: 'RESULTS',
      laPeak3: value,
    }));
  }, [clearTimer]);

  const handlePowerSample = useCallback((watts: number) => {
    if (phaseRef.current !== 'SPRINT_1' && phaseRef.current !== 'SPRINT_2' && phaseRef.current !== 'SPRINT_3') return;
    const elapsedMs = Date.now() - sprintStartRef.current;
    const sample: PowerSample = { elapsed_ms: elapsedMs, watts };

    setState(prev => {
      if (prev.phase === 'SPRINT_1') {
        return { ...prev, sprint1Samples: [...prev.sprint1Samples, sample] };
      } else if (prev.phase === 'SPRINT_2') {
        return { ...prev, sprint2Samples: [...prev.sprint2Samples, sample] };
      } else if (prev.phase === 'SPRINT_3') {
        return { ...prev, sprint3Samples: [...prev.sprint3Samples, sample] };
      }
      return prev;
    });
  }, []);

  const goToResults = useCallback(() => {
    clearTimer();
    setState(prev => ({ ...prev, phase: 'RESULTS' }));
  }, [clearTimer]);

  const reset = useCallback(() => {
    clearTimer();
    setState(initialState());
  }, [clearTimer]);

  return {
    state,
    beginProtocol,
    startProtocol,
    submitLactate,
    submitManualEntry,
    submitFinalLactate,
    handlePowerSample,
    goToResults,
    reset,
  };
}
