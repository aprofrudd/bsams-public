'use client';

import { useState } from 'react';
import { exercisesApi } from '@/lib/api';
import { ExerciseAutocomplete } from './ExerciseAutocomplete';
import { StepperInput } from './StepperInput';
import type { ExerciseLibraryItem, ExercisePrescription } from '@/lib/types';

interface SetConfig {
  reps: number;
  repDurations: number[];
  restBetweenReps: number[]; // length = reps - 1
  repIntensityValues: number[]; // length = reps
}

interface ConditioningExerciseFormProps {
  sessionId: string;
  nextSetNumber: number;
  existingExercises?: ExercisePrescription[];
  onSaved: () => void;
  onCancel: () => void;
}

const DEFAULT_SET: SetConfig = { reps: 1, repDurations: [30], restBetweenReps: [], repIntensityValues: [0] };

function selectOnFocus(e: React.FocusEvent<HTMLInputElement>) {
  e.target.select();
}

export function ConditioningExerciseForm({
  sessionId,
  nextSetNumber,
  existingExercises,
  onSaved,
  onCancel,
}: ConditioningExerciseFormProps) {
  const isEditMode = !!existingExercises && existingExercises.length > 0;

  function initSets(): SetConfig[] {
    if (!existingExercises || existingExercises.length === 0) return [{ ...DEFAULT_SET }];
    return existingExercises.map((ex) => ({
      reps: ex.reps || 1,
      repDurations: ex.rep_durations || (ex.duration_seconds ? [ex.duration_seconds] : [30]),
      restBetweenReps: ex.rest_between_reps || [],
      repIntensityValues: ex.rep_intensity_values || Array.from({ length: ex.reps || 1 }, () => 0),
    }));
  }

  function initRestBetweenSets(): number[] {
    if (!existingExercises || existingExercises.length <= 1) return [];
    return existingExercises.slice(0, -1).map((ex) => ex.rest_seconds || 60);
  }

  const [exerciseName, setExerciseName] = useState(
    existingExercises?.[0]?.exercise_name || ''
  );
  const [sets, setSets] = useState<SetConfig[]>(initSets);
  // restBetweenSetsArr[i] = rest (seconds) between set i and set i+1
  // Length is always sets.length - 1
  const [restBetweenSetsArr, setRestBetweenSetsArr] = useState<number[]>(initRestBetweenSets);
  const [intensityType, setIntensityType] = useState(
    existingExercises?.[0]?.intensity_type || ''
  );
  const [intensityValue, setIntensityValue] = useState(
    existingExercises?.[0]?.intensity_value != null ? String(existingExercises[0].intensity_value) : ''
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleLibrarySelect(item: ExerciseLibraryItem) {
    setExerciseName(item.exercise_name);
    if (item.default_intensity_type) setIntensityType(item.default_intensity_type);
    if (item.default_intensity_value) setIntensityValue(String(item.default_intensity_value));
    if (item.default_rep_durations) {
      const durations = item.default_rep_durations;
      const restArr = item.default_rest_between_reps
        || (item.default_rest_between_reps_seconds
          ? Array.from({ length: durations.length - 1 }, () => item.default_rest_between_reps_seconds!)
          : Array.from({ length: durations.length - 1 }, () => 0));
      const rivArr = item.default_rep_intensity_values
        || Array.from({ length: durations.length }, () => 0);
      setSets((prev) =>
        prev.map((s) => ({
          ...s,
          reps: durations.length,
          repDurations: [...durations],
          restBetweenReps: restArr.slice(0, durations.length - 1),
          repIntensityValues: rivArr.slice(0, durations.length),
        }))
      );
    } else if (item.default_duration_seconds) {
      setSets((prev) =>
        prev.map((s) => {
          const reps = item.default_reps || s.reps;
          return {
            ...s,
            reps,
            repDurations: Array.from({ length: reps }, () => item.default_duration_seconds!),
            restBetweenReps: item.default_rest_between_reps_seconds
              ? Array.from({ length: reps - 1 }, () => item.default_rest_between_reps_seconds!)
              : Array.from({ length: reps - 1 }, () => 0),
            repIntensityValues: syncRepIntensityValues(s.repIntensityValues, reps, 0),
          };
        })
      );
    } else if (item.default_reps) {
      setSets((prev) =>
        prev.map((s) => {
          const newReps = item.default_reps!;
          const lastDur = s.repDurations[s.repDurations.length - 1] || 30;
          return {
            ...s,
            reps: newReps,
            repDurations: syncRepDurations(s.repDurations, newReps, lastDur),
            restBetweenReps: syncRestBetweenReps(s.restBetweenReps, newReps,
              item.default_rest_between_reps_seconds || 0),
            repIntensityValues: syncRepIntensityValues(s.repIntensityValues, newReps, 0),
          };
        })
      );
    }
    if (item.default_rest_seconds) {
      const restVal = item.default_rest_seconds;
      setRestBetweenSetsArr((prev) => prev.map(() => restVal));
    }
  }

  /** Grow/shrink repDurations to match newReps count. */
  function syncRepDurations(current: number[], newReps: number, fallback: number): number[] {
    if (newReps <= current.length) return current.slice(0, newReps);
    const lastVal = current.length > 0 ? current[current.length - 1] : fallback;
    return [...current, ...Array.from({ length: newReps - current.length }, () => lastVal)];
  }

  /** Grow/shrink restBetweenReps to match newReps - 1 count. */
  function syncRestBetweenReps(current: number[], newReps: number, fallback: number): number[] {
    const targetLen = Math.max(0, newReps - 1);
    if (targetLen <= current.length) return current.slice(0, targetLen);
    const lastVal = current.length > 0 ? current[current.length - 1] : fallback;
    return [...current, ...Array.from({ length: targetLen - current.length }, () => lastVal)];
  }

  /** Grow/shrink repIntensityValues to match newReps count. */
  function syncRepIntensityValues(current: number[], newReps: number, fallback: number): number[] {
    if (newReps <= current.length) return current.slice(0, newReps);
    const lastVal = current.length > 0 ? current[current.length - 1] : fallback;
    return [...current, ...Array.from({ length: newReps - current.length }, () => lastVal)];
  }

  function handleSetCount(count: number) {
    setSets((prev) => {
      if (count > prev.length) {
        const last = prev[prev.length - 1];
        return [...prev, ...Array.from({ length: count - prev.length }, () => ({
          ...last,
          repDurations: [...last.repDurations],
          restBetweenReps: [...last.restBetweenReps],
          repIntensityValues: [...last.repIntensityValues],
        }))];
      }
      return prev.slice(0, count);
    });
    setRestBetweenSetsArr((prev) => {
      const newLen = count - 1;
      if (newLen <= 0) return [];
      if (newLen > prev.length) {
        const lastVal = prev.length > 0 ? prev[prev.length - 1] : 60;
        return [...prev, ...Array.from({ length: newLen - prev.length }, () => lastVal)];
      }
      return prev.slice(0, newLen);
    });
  }

  function handleCopySet(index: number) {
    setSets((prev) => [
      ...prev.slice(0, index + 1),
      { ...prev[index], repDurations: [...prev[index].repDurations], restBetweenReps: [...prev[index].restBetweenReps], repIntensityValues: [...prev[index].repIntensityValues] },
      ...prev.slice(index + 1),
    ]);
    setRestBetweenSetsArr((prev) => {
      const restToCopy = index < prev.length ? prev[index] : 60;
      return [
        ...prev.slice(0, index),
        restToCopy,
        ...prev.slice(index),
      ];
    });
  }

  function updateSetReps(index: number, newReps: number) {
    setSets((prev) => prev.map((s, i) => {
      if (i !== index) return s;
      return {
        ...s,
        reps: newReps,
        repDurations: syncRepDurations(s.repDurations, newReps, s.repDurations[s.repDurations.length - 1] || 30),
        restBetweenReps: syncRestBetweenReps(s.restBetweenReps, newReps,
          s.restBetweenReps.length > 0 ? s.restBetweenReps[s.restBetweenReps.length - 1] : 0),
        repIntensityValues: syncRepIntensityValues(s.repIntensityValues, newReps,
          s.repIntensityValues.length > 0 ? s.repIntensityValues[s.repIntensityValues.length - 1] : 0),
      };
    }));
  }

  function updateRepDuration(setIndex: number, repIndex: number, value: number) {
    setSets((prev) => prev.map((s, i) => {
      if (i !== setIndex) return s;
      const newDurations = [...s.repDurations];
      newDurations[repIndex] = value;
      return { ...s, repDurations: newDurations };
    }));
  }

  function updateRepRest(setIndex: number, restIndex: number, value: number) {
    setSets((prev) => prev.map((s, i) => {
      if (i !== setIndex) return s;
      const newRest = [...s.restBetweenReps];
      newRest[restIndex] = value;
      return { ...s, restBetweenReps: newRest };
    }));
  }

  function updateRepIntensity(setIndex: number, repIndex: number, value: number) {
    setSets((prev) => prev.map((s, i) => {
      if (i !== setIndex) return s;
      const newVals = [...s.repIntensityValues];
      newVals[repIndex] = value;
      return { ...s, repIntensityValues: newVals };
    }));
  }

  function updateRest(index: number, value: number) {
    setRestBetweenSetsArr((prev) => prev.map((r, i) => (i === index ? value : r)));
  }

  function buildExerciseData(s: SetConfig, i: number) {
    const hasRestArray = s.restBetweenReps.length > 0 && s.restBetweenReps.some(r => r > 0);
    const hasPerRepIntensity = intensityType && s.repIntensityValues.some(v => v > 0);
    return {
      exercise_name: exerciseName.trim(),
      exercise_category: 'Conditioning' as const,
      reps: s.reps,
      rep_durations: s.repDurations,
      duration_seconds: s.repDurations[0] || undefined,
      rest_between_reps: hasRestArray ? s.restBetweenReps : undefined,
      rest_between_reps_seconds: hasRestArray
        ? s.restBetweenReps[0]
        : undefined,
      rest_seconds: i < restBetweenSetsArr.length ? restBetweenSetsArr[i] : undefined,
      intensity_type: intensityType || undefined,
      intensity_value: hasPerRepIntensity
        ? s.repIntensityValues[0]
        : (intensityValue ? Number(intensityValue) : undefined),
      rep_intensity_values: hasPerRepIntensity ? s.repIntensityValues : undefined,
    };
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!exerciseName.trim()) return;

    setSaving(true);
    setError(null);
    try {
      if (isEditMode && existingExercises) {
        // Edit mode: update existing, create new, delete surplus
        for (let i = 0; i < sets.length; i++) {
          const data = buildExerciseData(sets[i], i);
          if (i < existingExercises.length) {
            // Update existing exercise
            await exercisesApi.update(sessionId, existingExercises[i].id, {
              ...data,
              set_number: existingExercises[i].set_number,
            });
          } else {
            // Create new exercise for additional sets
            const maxSetNum = existingExercises.length > 0
              ? Math.max(...existingExercises.map(ex => ex.set_number))
              : 0;
            await exercisesApi.create(sessionId, {
              ...data,
              set_number: maxSetNum + (i - existingExercises.length) + 1,
            });
          }
        }
        // Delete surplus exercises if sets reduced
        for (let i = sets.length; i < existingExercises.length; i++) {
          await exercisesApi.delete(sessionId, existingExercises[i].id);
        }
      } else {
        // Create mode
        for (let i = 0; i < sets.length; i++) {
          const data = buildExerciseData(sets[i], i);
          await exercisesApi.create(sessionId, {
            ...data,
            set_number: nextSetNumber + i,
          });
        }
      }
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : isEditMode ? 'Failed to update exercise' : 'Failed to add exercise');
    } finally {
      setSaving(false);
    }
  }

  const intensityUnit =
    intensityType === 'rpe' ? 'RPE'
      : intensityType === 'speed_kmh' ? 'km/h'
        : intensityType === 'power_watts' ? 'W'
          : '';

  // Show per-rep intensity inputs when an intensity type is selected
  const showPerRepIntensity = !!intensityType;

  return (
    <form onSubmit={handleSubmit} className="space-y-4 border-t border-secondary-muted/30 pt-3">
      {error && <p className="text-red-400 text-sm">{error}</p>}

      {/* Exercise Name */}
      <div>
        <label className="block text-xs text-white/60 mb-1">Exercise Name</label>
        <ExerciseAutocomplete
          value={exerciseName}
          onChange={setExerciseName}
          onSelect={handleLibrarySelect}
          categoryFilter="Conditioning"
          placeholder="e.g. HIIT, Tabata, Sprint Intervals..."
        />
      </div>

      {/* Number of Sets */}
      <div>
        <label className="block text-xs text-white/60 mb-2">Number of Sets</label>
        <StepperInput value={sets.length} onChange={handleSetCount} min={1} max={20} />
      </div>

      {/* Intensity Type */}
      <div>
        <label className="block text-xs text-white/60 mb-1">Intensity Type</label>
        <select
          value={intensityType}
          onChange={(e) => setIntensityType(e.target.value)}
          className="select w-full sm:w-48 text-sm"
        >
          <option value="">None</option>
          <option value="rpe">RPE</option>
          <option value="speed_kmh">Speed (km/h)</option>
          <option value="power_watts">Power (W)</option>
        </select>
        {showPerRepIntensity && (
          <p className="text-[10px] text-white/40 mt-1">Per-rep {intensityUnit} targets shown inline below</p>
        )}
      </div>

      {/* Per-Set Cards with Rest Separators */}
      <div className="space-y-0">
        {sets.map((s, i) => (
          <div key={i}>
            {/* Set card */}
            <div className="rounded-lg border border-secondary-muted/30 bg-secondary-muted/5 p-3">
              <div className="flex items-center justify-between mb-2">
                <div className="text-xs font-medium text-white/50 uppercase tracking-wider">
                  Set {i + 1}
                </div>
                <button
                  type="button"
                  onClick={() => handleCopySet(i)}
                  className="px-3 py-1.5 min-h-[44px] text-xs font-medium text-accent hover:bg-accent/10 rounded active:scale-[0.97] transition-colors"
                >
                  Copy Set
                </button>
              </div>
              <div className="space-y-3">
                <div>
                  <label className="block text-xs text-white/60 mb-1">Reps</label>
                  <StepperInput
                    value={s.reps}
                    onChange={(v) => updateSetReps(i, v)}
                    min={1}
                    max={50}
                  />
                </div>
                {/* Per-rep durations with rest between reps */}
                <div>
                  <label className="block text-xs text-white/60 mb-1">
                    {s.reps === 1 ? 'Duration (s)' : 'Rep Durations & Rest (s)'}
                  </label>
                  {s.reps === 1 ? (
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        min="1"
                        max="3600"
                        value={s.repDurations[0] || ''}
                        onChange={(e) =>
                          updateRepDuration(i, 0, e.target.value ? Number(e.target.value) : 0)
                        }
                        onFocus={selectOnFocus}
                        className="input w-full sm:w-32 text-sm"
                        placeholder="e.g. 30"
                      />
                      {showPerRepIntensity && (
                        <>
                          <span className="text-[10px] text-white/30">@</span>
                          <input
                            type="number"
                            step="any"
                            min="0"
                            value={s.repIntensityValues[0] || ''}
                            onChange={(e) =>
                              updateRepIntensity(i, 0, e.target.value ? Number(e.target.value) : 0)
                            }
                            onFocus={selectOnFocus}
                            className="input w-16 sm:w-20 text-sm text-center"
                            placeholder="0"
                          />
                          <span className="text-[10px] text-white/30">{intensityUnit}</span>
                        </>
                      )}
                    </div>
                  ) : (
                    <div className="space-y-1">
                      {s.repDurations.map((dur, ri) => (
                        <div key={ri}>
                          {/* Rep duration row */}
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] text-white/30 w-6 text-right shrink-0">R{ri + 1}</span>
                            <input
                              type="number"
                              min="1"
                              max="3600"
                              value={dur || ''}
                              onChange={(e) =>
                                updateRepDuration(i, ri, e.target.value ? Number(e.target.value) : 0)
                              }
                              onFocus={selectOnFocus}
                              className="input w-16 sm:w-20 text-sm text-center"
                              placeholder="30"
                            />
                            <span className="text-[10px] text-white/30">work</span>
                            {showPerRepIntensity && (
                              <>
                                <span className="text-[10px] text-white/30">@</span>
                                <input
                                  type="number"
                                  step="any"
                                  min="0"
                                  value={s.repIntensityValues[ri] || ''}
                                  onChange={(e) =>
                                    updateRepIntensity(i, ri, e.target.value ? Number(e.target.value) : 0)
                                  }
                                  onFocus={selectOnFocus}
                                  className="input w-16 sm:w-20 text-sm text-center"
                                  placeholder="0"
                                />
                                <span className="text-[10px] text-white/30">{intensityUnit}</span>
                              </>
                            )}
                          </div>
                          {/* Rest between reps (shown after each rep except last) */}
                          {ri < s.reps - 1 && (
                            <div className="flex items-center gap-2 ml-8 my-0.5">
                              <div className="w-px h-3 bg-secondary-muted/30" />
                              <input
                                type="number"
                                min="0"
                                max="600"
                                value={s.restBetweenReps[ri] ?? ''}
                                onChange={(e) =>
                                  updateRepRest(i, ri, e.target.value ? Number(e.target.value) : 0)
                                }
                                onFocus={selectOnFocus}
                                className="input w-14 sm:w-16 text-xs text-center"
                                placeholder="0"
                              />
                              <span className="text-[10px] text-white/30">rest</span>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Rest separator between sets */}
            {i < sets.length - 1 && (
              <div className="flex items-center gap-3 py-2 px-4">
                <div className="flex-1 border-t border-secondary-muted/20" />
                <div className="flex items-center gap-2">
                  <label className="text-xs text-white/40 whitespace-nowrap">Rest</label>
                  <input
                    type="number"
                    min="0"
                    max="600"
                    value={restBetweenSetsArr[i] ?? 60}
                    onChange={(e) =>
                      updateRest(i, e.target.value ? Number(e.target.value) : 0)
                    }
                    onFocus={selectOnFocus}
                    className="input w-16 sm:w-20 text-sm text-center"
                    placeholder="60"
                  />
                  <span className="text-xs text-white/40">sec</span>
                </div>
                <div className="flex-1 border-t border-secondary-muted/20" />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <button type="button" onClick={onCancel} className="btn-secondary text-sm">
          Cancel
        </button>
        <button
          type="submit"
          disabled={saving}
          className="btn-primary text-sm disabled:opacity-50"
        >
          {saving ? 'Saving...' : isEditMode ? 'Update Exercise' : 'Save'}
        </button>
      </div>
    </form>
  );
}
