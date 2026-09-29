'use client';

import { useState, useEffect } from 'react';
import { vbtApi } from '@/lib/api';
import { ResponsiveModal } from '@/components/ResponsiveModal';
import type { VbtProfile, VbtSetCreate } from '@/lib/types';

interface VbtProfileFormProps {
  athleteId: string;
  existingProfile?: VbtProfile | null;
  onClose: () => void;
  onSaved: () => void;
}

const EXERCISE_PRESETS = [
  'Trap Bar Deadlift',
  'Back Squat',
  'Front Squat',
  'Bench Press',
  'Overhead Press',
  'Landmine Punch Throw',
];

const DEFAULT_MVTS: Record<string, number> = {
  'trap bar deadlift': 0.30,
  'back squat': 0.30,
  'front squat': 0.30,
  'bench press': 0.17,
  'overhead press': 0.20,
  'landmine punch throw': 0.50,
};

interface SetRow {
  load_kg: string;
  mean_velocity_ms: string;
  peak_velocity_ms: string;
  reps: string;
}

function emptySet(): SetRow {
  return { load_kg: '', mean_velocity_ms: '', peak_velocity_ms: '', reps: '' };
}

export function VbtProfileForm({
  athleteId,
  existingProfile,
  onClose,
  onSaved,
}: VbtProfileFormProps) {
  const isEdit = !!existingProfile;

  const [exerciseName, setExerciseName] = useState(existingProfile?.exercise_name ?? '');
  const [profileDate, setProfileDate] = useState(
    existingProfile ? existingProfile.profile_date.slice(0, 10) : ''
  );
  const [mvtOverride, setMvtOverride] = useState(
    existingProfile?.mvt_ms != null ? String(existingProfile.mvt_ms) : ''
  );
  const [notes, setNotes] = useState(existingProfile?.notes ?? '');
  const [sets, setSets] = useState<SetRow[]>(() => {
    if (existingProfile?.sets?.length) {
      return existingProfile.sets.map((s) => ({
        load_kg: String(s.load_kg),
        mean_velocity_ms: s.mean_velocity_ms != null ? String(s.mean_velocity_ms) : '',
        peak_velocity_ms: s.peak_velocity_ms != null ? String(s.peak_velocity_ms) : '',
        reps: s.reps != null ? String(s.reps) : '',
      }));
    }
    return [emptySet(), emptySet(), emptySet()];
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showExerciseDropdown, setShowExerciseDropdown] = useState(false);

  const defaultMvt = DEFAULT_MVTS[exerciseName.toLowerCase().trim()] ?? 0.30;

  function updateSet(index: number, field: keyof SetRow, value: string) {
    setSets((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  }

  function removeSet(index: number) {
    if (sets.length <= 1) return;
    setSets((prev) => prev.filter((_, i) => i !== index));
  }

  function addSet() {
    setSets((prev) => [...prev, emptySet()]);
  }

  function validate(): string | null {
    if (!exerciseName.trim()) return 'Exercise name is required';
    if (!isEdit && !profileDate) return 'Profile date is required';

    // Need at least 2 sets with data for regression
    const filledSets = sets.filter(
      (s) => s.load_kg && (s.mean_velocity_ms || s.peak_velocity_ms)
    );
    if (filledSets.length < 2) {
      return 'At least 2 sets with load and velocity are required';
    }

    // Validate each filled set
    for (let i = 0; i < sets.length; i++) {
      const s = sets[i];
      if (!s.load_kg && !s.mean_velocity_ms && !s.peak_velocity_ms) continue;
      if (!s.load_kg) return `Set ${i + 1}: Load is required`;
      if (!s.mean_velocity_ms && !s.peak_velocity_ms) {
        return `Set ${i + 1}: At least one velocity is required`;
      }
      const load = Number(s.load_kg);
      if (isNaN(load) || load <= 0 || load > 1000) {
        return `Set ${i + 1}: Load must be 0–1000 kg`;
      }
      if (s.mean_velocity_ms) {
        const v = Number(s.mean_velocity_ms);
        if (isNaN(v) || v < 0 || v > 5) return `Set ${i + 1}: Mean velocity must be 0–5 m/s`;
      }
      if (s.peak_velocity_ms) {
        const v = Number(s.peak_velocity_ms);
        if (isNaN(v) || v < 0 || v > 10) return `Set ${i + 1}: Peak velocity must be 0–10 m/s`;
      }
    }
    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setSaving(true);
    setError(null);

    try {
      // Build sets (only include sets with data)
      const setsPayload: VbtSetCreate[] = sets
        .filter((s) => s.load_kg && (s.mean_velocity_ms || s.peak_velocity_ms))
        .map((s) => ({
          load_kg: Number(s.load_kg),
          ...(s.mean_velocity_ms ? { mean_velocity_ms: Number(s.mean_velocity_ms) } : {}),
          ...(s.peak_velocity_ms ? { peak_velocity_ms: Number(s.peak_velocity_ms) } : {}),
          ...(s.reps ? { reps: Number(s.reps) } : {}),
        }));

      if (isEdit && existingProfile) {
        await vbtApi.updateProfile(existingProfile.id, {
          exercise_name: exerciseName.trim(),
          ...(profileDate ? { profile_date: profileDate } : {}),
          ...(mvtOverride ? { mvt_ms: Number(mvtOverride) } : {}),
          notes: notes || undefined,
          sets: setsPayload,
        });
      } else {
        await vbtApi.createProfile(athleteId, {
          exercise_name: exerciseName.trim(),
          profile_date: profileDate,
          ...(mvtOverride ? { mvt_ms: Number(mvtOverride) } : {}),
          notes: notes || undefined,
          sets: setsPayload,
        });
      }

      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save profile');
    } finally {
      setSaving(false);
    }
  }

  const filteredPresets = EXERCISE_PRESETS.filter((p) =>
    p.toLowerCase().includes(exerciseName.toLowerCase().trim())
  );

  return (
    <ResponsiveModal isOpen={true} onClose={onClose} maxWidth="lg" title={isEdit ? 'Edit VBT Profile' : 'New VBT Profile'}>
        <form onSubmit={handleSubmit} className="space-y-3">
          {/* Exercise Name */}
          <div className="relative">
            <label className="block text-sm text-white/60 mb-1">Exercise</label>
            <input
              type="text"
              value={exerciseName}
              onChange={(e) => {
                setExerciseName(e.target.value);
                setShowExerciseDropdown(true);
              }}
              onFocus={() => setShowExerciseDropdown(true)}
              onBlur={() => setTimeout(() => setShowExerciseDropdown(false), 200)}
              className="input w-full"
              placeholder="e.g. Trap Bar Deadlift"
              required
            />
            {showExerciseDropdown && filteredPresets.length > 0 && exerciseName !== filteredPresets[0] && (
              <div className="absolute z-10 w-full mt-1 bg-[#07083D] border border-secondary-muted rounded-lg shadow-lg max-h-40 overflow-y-auto">
                {filteredPresets.map((preset) => (
                  <button
                    key={preset}
                    type="button"
                    onMouseDown={(e) => {
                      e.preventDefault();
                      setExerciseName(preset);
                      setShowExerciseDropdown(false);
                    }}
                    className="w-full text-left px-3 py-2 min-h-[44px] text-sm text-white/80 hover:bg-secondary-muted/50 active:bg-secondary-muted/70 transition-colors"
                  >
                    {preset}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Profile Date */}
          <div>
            <label className="block text-sm text-white/60 mb-1">Date</label>
            <input
              type="date"
              value={profileDate}
              onChange={(e) => setProfileDate(e.target.value)}
              className="input w-full"
              required={!isEdit}
            />
          </div>

          {/* MVT Override */}
          <div>
            <label className="block text-sm text-white/60 mb-1">
              MVT Override (m/s)
              <span className="text-white/40 ml-1">Default: {defaultMvt.toFixed(2)}</span>
            </label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              max="3"
              value={mvtOverride}
              onChange={(e) => setMvtOverride(e.target.value)}
              className="input w-full"
              placeholder={defaultMvt.toFixed(2)}
            />
          </div>

          {/* Load-Velocity Sets */}
          <div>
            <label className="block text-sm text-white/60 mb-2">Load-Velocity Sets</label>

            {/* Desktop Header */}
            <div className="hidden sm:grid grid-cols-[1fr_1fr_1fr_auto_auto] gap-2 text-xs text-white/40 mb-1 px-1">
              <span>Load (kg)</span>
              <span>Mean V (m/s)</span>
              <span>Peak V (m/s)</span>
              <span>Reps</span>
              <span></span>
            </div>

            <div className="space-y-2">
              {sets.map((s, i) => (
                <div key={i}>
                  {/* Desktop row */}
                  <div className="hidden sm:grid grid-cols-[1fr_1fr_1fr_auto_auto] gap-2 items-center">
                    <input
                      type="number"
                      step="any"
                      min="0"
                      max="1000"
                      value={s.load_kg}
                      onChange={(e) => updateSet(i, 'load_kg', e.target.value)}
                      className="input w-full"
                      placeholder="kg"
                    />
                    <input
                      type="number"
                      step="0.001"
                      min="0"
                      max="5"
                      value={s.mean_velocity_ms}
                      onChange={(e) => updateSet(i, 'mean_velocity_ms', e.target.value)}
                      className="input w-full"
                      placeholder="m/s"
                    />
                    <input
                      type="number"
                      step="0.001"
                      min="0"
                      max="10"
                      value={s.peak_velocity_ms}
                      onChange={(e) => updateSet(i, 'peak_velocity_ms', e.target.value)}
                      className="input w-full"
                      placeholder="m/s"
                    />
                    <input
                      type="number"
                      min="1"
                      max="20"
                      value={s.reps}
                      onChange={(e) => updateSet(i, 'reps', e.target.value)}
                      className="input w-14"
                      placeholder="#"
                    />
                    <button
                      type="button"
                      onClick={() => removeSet(i)}
                      disabled={sets.length <= 1}
                      className="text-white/30 hover:text-red-400 active:text-red-300 disabled:opacity-20 p-2 min-h-[44px] min-w-[44px] flex items-center justify-center"
                      title="Remove set"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4">
                        <path fillRule="evenodd" d="M5 3.25V4H2.75a.75.75 0 0 0 0 1.5h.3l.815 8.15A1.5 1.5 0 0 0 5.357 15h5.285a1.5 1.5 0 0 0 1.493-1.35l.815-8.15h.3a.75.75 0 0 0 0-1.5H11v-.75A2.25 2.25 0 0 0 8.75 1h-1.5A2.25 2.25 0 0 0 5 3.25Zm2.25-.75a.75.75 0 0 0-.75.75V4h3v-.75a.75.75 0 0 0-.75-.75h-1.5ZM6.05 6a.75.75 0 0 1 .787.713l.275 5.5a.75.75 0 0 1-1.498.075l-.275-5.5A.75.75 0 0 1 6.05 6Zm3.9 0a.75.75 0 0 1 .712.787l-.275 5.5a.75.75 0 0 1-1.498-.075l.275-5.5a.75.75 0 0 1 .786-.711Z" clipRule="evenodd" />
                      </svg>
                    </button>
                  </div>

                  {/* Mobile row */}
                  <div className="sm:hidden space-y-1.5 border border-secondary-muted/50 rounded-lg p-2">
                    <div className="text-xs text-white/40">Set {i + 1}</div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-xs text-white/40">Load (kg)</label>
                        <input
                          type="number"
                          step="any"
                          min="0"
                          max="1000"
                          value={s.load_kg}
                          onChange={(e) => updateSet(i, 'load_kg', e.target.value)}
                          className="input w-full"
                          placeholder="kg"
                        />
                      </div>
                      <div>
                        <label className="text-xs text-white/40">Reps</label>
                        <input
                          type="number"
                          min="1"
                          max="20"
                          value={s.reps}
                          onChange={(e) => updateSet(i, 'reps', e.target.value)}
                          className="input w-full"
                          placeholder="#"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-xs text-white/40">Mean V (m/s)</label>
                        <input
                          type="number"
                          step="0.001"
                          min="0"
                          max="5"
                          value={s.mean_velocity_ms}
                          onChange={(e) => updateSet(i, 'mean_velocity_ms', e.target.value)}
                          className="input w-full"
                          placeholder="m/s"
                        />
                      </div>
                      <div>
                        <label className="text-xs text-white/40">Peak V (m/s)</label>
                        <input
                          type="number"
                          step="0.001"
                          min="0"
                          max="10"
                          value={s.peak_velocity_ms}
                          onChange={(e) => updateSet(i, 'peak_velocity_ms', e.target.value)}
                          className="input w-full"
                          placeholder="m/s"
                        />
                      </div>
                    </div>
                    {sets.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeSet(i)}
                        className="text-xs text-red-400/60 hover:text-red-400 active:text-red-300 min-h-[44px] flex items-center"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <button
              type="button"
              onClick={addSet}
              className="mt-2 text-sm text-accent hover:text-accent/80 active:text-accent/60 min-h-[44px] flex items-center transition-colors"
            >
              + Add Set
            </button>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm text-white/60 mb-1">Notes</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="input w-full"
              rows={2}
              placeholder="Optional notes..."
              maxLength={1000}
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
              {saving ? 'Saving...' : isEdit ? 'Update' : 'Create Profile'}
            </button>
          </div>
        </form>
    </ResponsiveModal>
  );
}
