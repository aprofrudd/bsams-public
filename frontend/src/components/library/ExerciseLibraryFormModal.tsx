'use client';

import { useState } from 'react';
import { exerciseLibraryApi } from '@/lib/api';
import { ResponsiveModal } from '@/components/ResponsiveModal';
import type { ExerciseLibraryItem, ExerciseLibraryCreate as LibCreate, ExerciseLibraryUpdate as LibUpdate } from '@/lib/types';

interface ExerciseLibraryFormModalProps {
  existingExercise?: ExerciseLibraryItem | null;
  presetCategory?: string;
  onClose: () => void;
  onSaved: () => void;
}

interface SetConfig {
  reps: string;
  weight_kg: string;
}

const EXERCISE_CATEGORIES = ['Strength', 'Plyometric', 'Conditioning', 'Circuit', 'Other'];

function initSetConfigs(existing?: ExerciseLibraryItem | null): SetConfig[] {
  if (existing?.default_set_configs && existing.default_set_configs.length > 0) {
    return existing.default_set_configs.map(c => ({
      reps: c.reps != null ? String(c.reps) : '',
      weight_kg: c.weight_kg != null ? String(c.weight_kg) : '',
    }));
  }
  if (existing?.default_reps || existing?.default_weight_kg) {
    return [{
      reps: existing.default_reps ? String(existing.default_reps) : '',
      weight_kg: existing.default_weight_kg ? String(existing.default_weight_kg) : '',
    }];
  }
  return [{ reps: '', weight_kg: '' }];
}

function selectOnFocus(e: React.FocusEvent<HTMLInputElement>) {
  e.target.select();
}

export function ExerciseLibraryFormModal({
  existingExercise,
  presetCategory,
  onClose,
  onSaved,
}: ExerciseLibraryFormModalProps) {
  const isEdit = !!existingExercise;

  const [exerciseName, setExerciseName] = useState(existingExercise?.exercise_name || '');
  const [category, setCategory] = useState(existingExercise?.exercise_category || presetCategory || 'Strength');
  const [showCategoryDropdown, setShowCategoryDropdown] = useState(!presetCategory || isEdit);
  const [setConfigs, setSetConfigs] = useState<SetConfig[]>(() => initSetConfigs(existingExercise));
  const [defaultIntensityType, setDefaultIntensityType] = useState(existingExercise?.default_intensity_type || '');
  const [defaultIntensityValue, setDefaultIntensityValue] = useState(
    existingExercise?.default_intensity_value ? String(existingExercise.default_intensity_value) : ''
  );
  const [defaultRestBetweenReps, setDefaultRestBetweenReps] = useState(
    existingExercise?.default_rest_between_reps_seconds ? String(existingExercise.default_rest_between_reps_seconds) : ''
  );
  const [defaultDuration, setDefaultDuration] = useState(
    existingExercise?.default_duration_seconds ? String(existingExercise.default_duration_seconds) : ''
  );
  const [defaultRest, setDefaultRest] = useState(
    existingExercise?.default_rest_seconds ? String(existingExercise.default_rest_seconds) : ''
  );
  const [videoUrl, setVideoUrl] = useState(existingExercise?.video_url || '');
  const [notes, setNotes] = useState(existingExercise?.notes || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isConditioning = category === 'Conditioning';
  const isCircuit = category === 'Circuit';
  const numberOfSets = setConfigs.length;

  function handleSetCount(count: number) {
    setSetConfigs(prev => {
      if (count > prev.length) {
        const last = prev[prev.length - 1];
        return [...prev, ...Array.from({ length: count - prev.length }, () => ({ ...last }))];
      }
      return prev.slice(0, count);
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!exerciseName.trim()) {
      setError('Exercise name is required');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      // Build set configs array for non-conditioning
      let defaultSetConfigs: { reps?: number; weight_kg?: number }[] | undefined;
      let defaultRepsVal: number | undefined;
      let defaultWeightVal: number | undefined;

      if (!isConditioning) {
        const configs = setConfigs
          .map(sc => {
            const entry: { reps?: number; weight_kg?: number } = {};
            if (sc.reps) entry.reps = Number(sc.reps);
            if (sc.weight_kg) entry.weight_kg = Number(sc.weight_kg);
            return entry;
          })
          .filter(entry => entry.reps !== undefined || entry.weight_kg !== undefined);

        if (configs.length > 0) {
          defaultSetConfigs = configs;
          // Backward compat: first set values populate flat fields
          defaultRepsVal = configs[0].reps;
          defaultWeightVal = configs[0].weight_kg;
        }
      } else {
        // For conditioning, use the first set config's reps if present
        const firstReps = setConfigs[0]?.reps;
        if (firstReps) defaultRepsVal = Number(firstReps);
      }

      const data = {
        exercise_name: exerciseName.trim(),
        exercise_category: category || undefined,
        default_reps: defaultRepsVal,
        default_weight_kg: defaultWeightVal,
        default_set_configs: defaultSetConfigs,
        default_intensity_type: defaultIntensityType || undefined,
        default_intensity_value: defaultIntensityValue ? Number(defaultIntensityValue) : undefined,
        default_rest_between_reps_seconds: defaultRestBetweenReps ? Number(defaultRestBetweenReps) : undefined,
        default_duration_seconds: defaultDuration ? Number(defaultDuration) : undefined,
        default_rest_seconds: defaultRest ? Number(defaultRest) : undefined,
        video_url: videoUrl.trim() || undefined,
        notes: notes || undefined,
      };

      if (isEdit && existingExercise) {
        await exerciseLibraryApi.update(existingExercise.id, data as LibUpdate);
      } else {
        await exerciseLibraryApi.create(data as LibCreate);
      }
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save exercise');
    } finally {
      setSaving(false);
    }
  }

  return (
    <ResponsiveModal isOpen={true} onClose={onClose} maxWidth="md" title={isEdit ? 'Edit Exercise' : 'Add Exercise'}>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-sm text-white/60 mb-1">Exercise Name</label>
            <input
              type="text"
              value={exerciseName}
              onChange={(e) => setExerciseName(e.target.value)}
              className="input w-full"
              placeholder="e.g. Back Squat"
              required
            />
          </div>

          <div>
            <label className="block text-sm text-white/60 mb-1">Category</label>
            {showCategoryDropdown ? (
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="select w-full"
              >
                {EXERCISE_CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            ) : (
              <div className="flex items-center gap-2">
                <span className="px-3 py-1.5 rounded-full text-xs font-medium bg-accent/15 text-accent">{category}</span>
                <button
                  type="button"
                  onClick={() => setShowCategoryDropdown(true)}
                  className="text-xs text-white/40 hover:text-accent transition-colors"
                >
                  Change
                </button>
              </div>
            )}
          </div>

          {isCircuit ? (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm text-white/60 mb-1">Default Work Duration (s)</label>
                <input type="number" min="1" max="600" value={defaultDuration} onChange={(e) => setDefaultDuration(e.target.value)} className="input w-full" placeholder="e.g. 30" />
              </div>
              <div>
                <label className="block text-sm text-white/60 mb-1">Default Rest (s)</label>
                <input
                  type="number"
                  min="0"
                  max="600"
                  value={defaultRest}
                  onChange={(e) => setDefaultRest(e.target.value)}
                  className="input w-full"
                  placeholder="e.g. 10"
                />
              </div>
            </div>
          ) : isConditioning ? (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm text-white/60 mb-1">Default Reps</label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={setConfigs[0]?.reps ?? ''}
                  onChange={(e) => setSetConfigs(prev => prev.map((s, i) => i === 0 ? { ...s, reps: e.target.value } : s))}
                  className="input w-full"
                />
              </div>
              <div>
                <label className="block text-sm text-white/60 mb-1">Default Intensity Type</label>
                <select value={defaultIntensityType} onChange={(e) => setDefaultIntensityType(e.target.value)} className="select w-full">
                  <option value="">None</option>
                  <option value="rpe">RPE</option>
                  <option value="speed_kmh">Speed (km/h)</option>
                  <option value="power_watts">Power (W)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-white/60 mb-1">Default Intensity Value</label>
                <input type="number" step="any" min="0" value={defaultIntensityValue} onChange={(e) => setDefaultIntensityValue(e.target.value)} className="input w-full" />
              </div>
              <div>
                <label className="block text-sm text-white/60 mb-1">Default Work Duration (s)</label>
                <input type="number" min="1" max="600" value={defaultDuration} onChange={(e) => setDefaultDuration(e.target.value)} className="input w-full" placeholder="e.g. 30" />
              </div>
              <div>
                <label className="block text-sm text-white/60 mb-1">Default Rest Between Reps (s)</label>
                <input type="number" min="0" max="600" value={defaultRestBetweenReps} onChange={(e) => setDefaultRestBetweenReps(e.target.value)} className="input w-full" />
              </div>
              <div>
                <label className="block text-sm text-white/60 mb-1">Default Rest (s)</label>
                <input
                  type="number"
                  min="0"
                  max="600"
                  value={defaultRest}
                  onChange={(e) => setDefaultRest(e.target.value)}
                  className="input w-full"
                />
              </div>
            </div>
          ) : (
            <>
              {/* Sets stepper */}
              <div>
                <label className="block text-sm text-white/60 mb-2">Number of Sets</label>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => numberOfSets > 1 && handleSetCount(numberOfSets - 1)}
                    className="w-10 h-10 rounded bg-secondary-muted/20 text-white/60 hover:bg-secondary-muted/40 flex items-center justify-center text-lg font-bold transition-colors"
                  >
                    &minus;
                  </button>
                  <span className="w-8 text-center text-sm font-medium">{numberOfSets}</span>
                  <button
                    type="button"
                    onClick={() => numberOfSets < 20 && handleSetCount(numberOfSets + 1)}
                    className="w-10 h-10 rounded bg-secondary-muted/20 text-white/60 hover:bg-secondary-muted/40 flex items-center justify-center text-lg font-bold transition-colors"
                  >
                    +
                  </button>
                </div>
              </div>

              {/* Per-set cards */}
              <div className="space-y-0">
                {setConfigs.map((sc, i) => (
                  <div key={i} className="rounded bg-secondary-muted/5 px-3 py-2">
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-white/50 w-10 shrink-0">Set {i + 1}</span>
                      <input
                        type="number"
                        min="1"
                        max="100"
                        value={sc.reps}
                        onChange={(e) =>
                          setSetConfigs(prev => prev.map((s, idx) => idx === i ? { ...s, reps: e.target.value } : s))
                        }
                        onFocus={selectOnFocus}
                        className="input w-20 text-sm text-center"
                        placeholder="reps"
                      />
                      <span className="text-xs text-white/40">reps @</span>
                      <input
                        type="number"
                        step="any"
                        min="0"
                        value={sc.weight_kg}
                        onChange={(e) =>
                          setSetConfigs(prev => prev.map((s, idx) => idx === i ? { ...s, weight_kg: e.target.value } : s))
                        }
                        onFocus={selectOnFocus}
                        className="input w-20 text-sm text-center"
                        placeholder="kg"
                      />
                      <span className="text-xs text-white/40">kg</span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Rest */}
              <div>
                <label className="block text-sm text-white/60 mb-1">Default Rest (s)</label>
                <input
                  type="number"
                  min="0"
                  max="600"
                  value={defaultRest}
                  onChange={(e) => setDefaultRest(e.target.value)}
                  className="input w-full"
                />
              </div>
            </>
          )}

          <div>
            <label className="block text-sm text-white/60 mb-1">Video URL (optional)</label>
            <input
              type="url"
              value={videoUrl}
              onChange={(e) => setVideoUrl(e.target.value)}
              className="input w-full"
              placeholder="https://youtube.com/watch?v=..."
              maxLength={500}
            />
          </div>

          <div>
            <label className="block text-sm text-white/60 mb-1">Notes (optional)</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="input w-full resize-none"
              rows={2}
              maxLength={500}
              placeholder="Coaching cues, notes..."
            />
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary flex-1"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="btn-primary flex-1 disabled:opacity-50"
            >
              {saving ? 'Saving...' : isEdit ? 'Update' : 'Add Exercise'}
            </button>
          </div>
        </form>
    </ResponsiveModal>
  );
}
