'use client';

import { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useIntervalTimer, TimerExercise } from './useIntervalTimer';
import { useTimerAudio } from './useTimerAudio';
import { trainingApi } from '@/lib/api';

interface IntervalTimerProps {
  sessionId: string;
  exercises: TimerExercise[];
  onClose: () => void;
  onSaved?: () => void;
}

const PHASE_COLORS: Record<string, string> = {
  warmup: '#33CBF4',
  countdown: '#F59E0B',
  work: '#EF4444',
  rest: '#22C55E',
  complete: '#33CBF4',
};

const PHASE_LABELS: Record<string, string> = {
  warmup: 'Warm Up',
  countdown: 'Get Ready',
  work: 'WORK',
  rest: 'REST',
  complete: 'Complete',
};

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function IntervalTimer({ sessionId, exercises, onClose, onSaved }: IntervalTimerProps) {
  const { state, start, startCountdown, pause, resume, skip, end } = useIntervalTimer(exercises);
  const { playCountdownBeep, playTransitionBeep, initAudio } = useTimerAudio();
  const [showSaveForm, setShowSaveForm] = useState(false);
  const [sessionRpe, setSessionRpe] = useState('7');
  const [saving, setSaving] = useState(false);
  const prevPhaseRef = useRef(state.phase);
  const prevTimeRef = useRef(state.timeRemaining);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    return () => setMounted(false);
  }, []);

  // Audio cues
  useEffect(() => {
    // Phase transition beep
    if (prevPhaseRef.current !== state.phase) {
      if (state.phase === 'work' || state.phase === 'rest') {
        playTransitionBeep();
      }
      prevPhaseRef.current = state.phase;
    }

    // Countdown beeps at 3, 2, 1
    if (state.phase === 'countdown') {
      const prev = Math.ceil(prevTimeRef.current);
      const curr = Math.ceil(state.timeRemaining);
      if (prev !== curr && curr <= 3 && curr >= 1) {
        playCountdownBeep();
      }
    }

    prevTimeRef.current = state.timeRemaining;
  }, [state.phase, state.timeRemaining, playCountdownBeep, playTransitionBeep]);

  // Show save form on complete
  useEffect(() => {
    if (state.phase === 'complete') {
      setShowSaveForm(true);
    }
  }, [state.phase]);

  const currentExercise = exercises[state.currentExerciseIndex];
  const color = PHASE_COLORS[state.phase] || '#33CBF4';
  const label = PHASE_LABELS[state.phase] || '';

  // SVG circle math
  const radius = 110;
  const circumference = 2 * Math.PI * radius;
  const progress = state.totalDuration > 0
    ? (state.timeRemaining / state.totalDuration)
    : 1;
  const dashoffset = circumference * (1 - progress);

  async function handleSave() {
    setSaving(true);
    try {
      const durationMinutes = Math.round(state.totalElapsed / 60);
      await trainingApi.updateSession(sessionId, {
        rpe: Number(sessionRpe),
        duration_minutes: durationMinutes || 1,
      });
      onSaved?.();
      onClose();
    } catch (err) {
      console.error('Failed to save session:', err);
      onClose();
    } finally {
      setSaving(false);
    }
  }

  function handleStartSession() {
    initAudio();
    start();
  }

  function handleBeginWorkout() {
    startCountdown();
  }

  const content = (
    <div className="fixed inset-0 z-[100] bg-[#090A3D] flex flex-col items-center justify-center p-4">
      {/* Close button */}
      <button
        onClick={onClose}
        className="absolute top-4 right-4 text-white/40 hover:text-white text-2xl p-2"
        title="Close timer"
      >
        &#10005;
      </button>

      {/* Phase label */}
      <div className="text-center mb-6">
        <span
          className="text-lg font-bold uppercase tracking-widest"
          style={{ color }}
        >
          {label}
        </span>
      </div>

      {/* SVG circular timer */}
      <div className="relative w-[240px] h-[240px] mb-6">
        <svg viewBox="0 0 240 240" className="w-full h-full -rotate-90">
          {/* Background circle */}
          <circle
            cx="120" cy="120" r={radius}
            fill="none"
            stroke="rgba(255,255,255,0.1)"
            strokeWidth="8"
          />
          {/* Progress circle */}
          {state.phase !== 'idle' && state.phase !== 'warmup' && (
            <circle
              cx="120" cy="120" r={radius}
              fill="none"
              stroke={color}
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={dashoffset}
              style={{ transition: 'stroke-dashoffset 0.1s linear' }}
            />
          )}
        </svg>
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-4xl font-bold text-white font-mono">
            {state.phase === 'warmup'
              ? formatTime(state.warmupElapsed)
              : state.phase === 'idle'
              ? '0:00'
              : formatTime(state.timeRemaining)}
          </span>
          {state.phase === 'warmup' && (
            <span className="text-sm text-white/60 mt-1">elapsed</span>
          )}
        </div>
      </div>

      {/* Exercise info */}
      {currentExercise && state.phase !== 'idle' && state.phase !== 'complete' && (
        <div className="text-center mb-6 space-y-1">
          <p className="text-xl font-semibold text-white">{currentExercise.exercise_name}</p>
          <p className="text-sm text-white/60">
            Set {state.currentSet}/{currentExercise.sets.length} &middot; Rep {state.currentRep}/{currentExercise.sets[state.currentSet - 1]?.reps || 1}
          </p>
          {currentExercise.sets[state.currentSet - 1]?.rep_durations && (
            <p className="text-xs text-white/40">
              Rep duration: {currentExercise.sets[state.currentSet - 1].rep_durations![state.currentRep - 1]}s
            </p>
          )}
          {currentExercise.intensity_type && (() => {
            const currentSetConfig = currentExercise.sets[state.currentSet - 1];
            const perRepVal = currentSetConfig?.rep_intensity_values?.[state.currentRep - 1];
            const displayVal = perRepVal ?? currentExercise.intensity_value;
            const hasRange = currentExercise.intensity_min != null && currentExercise.intensity_max != null;

            if (!hasRange && displayVal == null) return null;

            const formatVal = (v: number) => {
              if (currentExercise.intensity_type === 'rpe') return `RPE ${v}`;
              if (currentExercise.intensity_type === 'speed_kmh') return `${v} km/h`;
              return `${Math.round(v)}W`;
            };

            const formatRange = (min: number, max: number) => {
              if (currentExercise.intensity_type === 'rpe') return `RPE ${min}-${max}`;
              if (currentExercise.intensity_type === 'speed_kmh') return `${min}-${max} km/h`;
              return `${Math.round(min)}-${Math.round(max)}W`;
            };

            return (
              <p className="text-sm font-medium" style={{ color }}>
                Target: {hasRange
                  ? formatRange(currentExercise.intensity_min!, currentExercise.intensity_max!)
                  : formatVal(displayVal!)}
              </p>
            );
          })()}
          {exercises.length > 1 && (
            <p className="text-xs text-white/40">
              Exercise {state.currentExerciseIndex + 1} of {exercises.length}
            </p>
          )}
        </div>
      )}

      {/* Total elapsed */}
      {state.phase !== 'idle' && (
        <p className="text-xs text-white/40 mb-4">
          Total: {formatTime(state.totalElapsed)}
        </p>
      )}

      {/* Controls */}
      <div className="flex items-center gap-3">
        {state.phase === 'idle' && (
          <button
            onClick={handleStartSession}
            className="px-8 py-3 rounded-lg text-lg font-semibold bg-accent text-[#090A3D] hover:bg-accent/80 active:scale-[0.97] transition-all"
          >
            Start Warm-Up
          </button>
        )}

        {state.phase === 'warmup' && !state.isPaused && (
          <button
            onClick={handleBeginWorkout}
            className="px-8 py-3 rounded-lg text-lg font-semibold bg-accent text-[#090A3D] hover:bg-accent/80 active:scale-[0.97] transition-all"
          >
            Begin Workout
          </button>
        )}

        {(state.phase === 'countdown' || state.phase === 'work' || state.phase === 'rest') && (
          <>
            {state.isPaused ? (
              <button
                onClick={resume}
                className="px-6 py-3 rounded-lg font-semibold bg-accent text-[#090A3D] hover:bg-accent/80 active:scale-[0.97] transition-all"
              >
                Resume
              </button>
            ) : (
              <button
                onClick={pause}
                className="px-6 py-3 rounded-lg font-semibold bg-white/10 text-white hover:bg-white/20 active:scale-[0.97] transition-all"
              >
                Pause
              </button>
            )}
            <button
              onClick={skip}
              className="px-4 py-3 rounded-lg font-medium text-white/60 hover:text-white hover:bg-white/10 active:scale-[0.97] transition-all"
            >
              Skip
            </button>
            <button
              onClick={end}
              className="px-4 py-3 rounded-lg font-medium text-red-400/60 hover:text-red-400 hover:bg-red-400/10 active:scale-[0.97] transition-all"
            >
              End
            </button>
          </>
        )}

        {state.phase === 'complete' && !showSaveForm && (
          <button
            onClick={onClose}
            className="px-8 py-3 rounded-lg text-lg font-semibold bg-accent text-[#090A3D] hover:bg-accent/80 active:scale-[0.97] transition-all"
          >
            Close
          </button>
        )}
      </div>

      {/* Save form overlay */}
      {showSaveForm && state.phase === 'complete' && (
        <div className="mt-6 bg-white/5 border border-white/10 rounded-lg p-6 w-full max-w-sm">
          <h3 className="text-lg font-semibold text-white mb-4">Save Session</h3>
          <div className="space-y-3">
            <div>
              <label className="block text-sm text-white/60 mb-1">Session RPE (1-10)</label>
              <input
                type="range"
                min="1"
                max="10"
                value={sessionRpe}
                onChange={(e) => setSessionRpe(e.target.value)}
                className="w-full"
              />
              <div className="text-center text-xl font-bold text-accent">{sessionRpe}</div>
            </div>
            <div>
              <label className="block text-sm text-white/60 mb-1">Duration</label>
              <p className="text-white font-medium">{Math.round(state.totalElapsed / 60)} minutes</p>
            </div>
            <div className="flex gap-3 pt-2">
              <button
                onClick={onClose}
                className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium bg-white/10 text-white hover:bg-white/20 active:scale-[0.97] transition-all"
              >
                Skip Save
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex-1 px-4 py-2.5 rounded-lg text-sm font-semibold bg-accent text-[#090A3D] hover:bg-accent/80 active:scale-[0.97] disabled:opacity-50 transition-all"
              >
                {saving ? 'Saving...' : 'Save & Close'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  if (!mounted) return null;
  return createPortal(content, document.body);
}
