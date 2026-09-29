'use client';

import { useState } from 'react';
import { exercisesApi } from '@/lib/api';
import { ExerciseAutocomplete } from './ExerciseAutocomplete';
import { StepperInput } from './StepperInput';
import type { ExerciseLibraryItem, ExercisePrescription } from '@/lib/types';

interface CircuitExercise {
  key: number;
  exercise_name: string;
  duration_seconds: number;
  rest_seconds: number;
}

interface CircuitExerciseFormProps {
  sessionId: string;
  nextSetNumber: number;
  existingExercises?: ExercisePrescription[];
  onSaved: () => void;
  onCancel: () => void;
}

let circuitKeyCounter = 0;
function nextKey() {
  return ++circuitKeyCounter;
}

function createEmptyExercise(): CircuitExercise {
  return { key: nextKey(), exercise_name: '', duration_seconds: 30, rest_seconds: 10 };
}

/**
 * Reconstruct circuit state from existing interleaved prescriptions.
 * Unique exercise names (in set_number order) = exercise list.
 * rounds = totalRows / uniqueExercises.length
 */
function reconstructFromExisting(exercises: ExercisePrescription[]) {
  const sorted = [...exercises].sort((a, b) => a.set_number - b.set_number);
  const seen = new Map<string, CircuitExercise>();
  const order: string[] = [];

  for (const ex of sorted) {
    if (!seen.has(ex.exercise_name)) {
      seen.set(ex.exercise_name, {
        key: nextKey(),
        exercise_name: ex.exercise_name,
        duration_seconds: ex.duration_seconds ?? 30,
        rest_seconds: ex.rest_seconds ?? 10,
      });
      order.push(ex.exercise_name);
    }
  }

  const uniqueCount = order.length;
  const rounds = uniqueCount > 0 ? Math.round(sorted.length / uniqueCount) : 1;

  // Round rest = rest_seconds of last exercise in first round
  const roundRest = uniqueCount > 0 && sorted.length >= uniqueCount
    ? sorted[uniqueCount - 1].rest_seconds ?? 60
    : 60;

  return {
    exercises: order.map(name => seen.get(name)!),
    rounds,
    roundRest,
  };
}

export function CircuitExerciseForm({
  sessionId,
  nextSetNumber,
  existingExercises,
  onSaved,
  onCancel,
}: CircuitExerciseFormProps) {
  const isEditMode = !!existingExercises && existingExercises.length > 0;

  const initial = isEditMode
    ? reconstructFromExisting(existingExercises!)
    : { exercises: [createEmptyExercise()], rounds: 3, roundRest: 60 };

  const [exercises, setExercises] = useState<CircuitExercise[]>(initial.exercises);
  const [rounds, setRounds] = useState(initial.rounds);
  const [roundRest, setRoundRest] = useState(initial.roundRest);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function selectOnFocus(e: React.FocusEvent<HTMLInputElement>) {
    e.target.select();
  }

  function updateExercise(index: number, field: keyof CircuitExercise, value: string | number) {
    setExercises(prev => prev.map((ex, i) =>
      i === index ? { ...ex, [field]: value } : ex
    ));
  }

  function handleLibrarySelect(index: number, item: ExerciseLibraryItem) {
    setExercises(prev => prev.map((ex, i) =>
      i === index ? {
        ...ex,
        exercise_name: item.exercise_name,
        duration_seconds: item.default_duration_seconds ?? ex.duration_seconds,
        rest_seconds: item.default_rest_seconds ?? ex.rest_seconds,
      } : ex
    ));
  }

  function addExercise() {
    setExercises(prev => [...prev, createEmptyExercise()]);
  }

  function removeExercise(index: number) {
    if (exercises.length <= 1) return;
    setExercises(prev => prev.filter((_, i) => i !== index));
  }

  function moveExercise(index: number, direction: 'up' | 'down') {
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= exercises.length) return;
    setExercises(prev => {
      const updated = [...prev];
      [updated[index], updated[newIndex]] = [updated[newIndex], updated[index]];
      return updated;
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const validExercises = exercises.filter(ex => ex.exercise_name.trim());
    if (validExercises.length === 0) return;

    setSaving(true);
    setError(null);

    try {
      // Delete existing prescriptions if editing
      if (isEditMode && existingExercises) {
        for (const ex of existingExercises) {
          await exercisesApi.delete(sessionId, ex.id);
        }
      }

      // Create interleaved prescriptions: for each round, emit all exercises in order
      let setCounter = nextSetNumber;
      if (isEditMode && existingExercises && existingExercises.length > 0) {
        // Use the minimum set_number from existing as base
        setCounter = Math.min(...existingExercises.map(ex => ex.set_number));
      }

      for (let round = 0; round < rounds; round++) {
        for (let i = 0; i < validExercises.length; i++) {
          const ex = validExercises[i];
          const isLastInRound = i === validExercises.length - 1;
          await exercisesApi.create(sessionId, {
            exercise_name: ex.exercise_name.trim(),
            exercise_category: 'Circuit',
            set_number: setCounter,
            duration_seconds: ex.duration_seconds,
            rest_seconds: isLastInRound ? roundRest : ex.rest_seconds,
          });
          setCounter++;
        }
      }

      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save circuit');
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 border-t border-secondary-muted/30 pt-3">
      {error && <p className="text-red-400 text-sm">{error}</p>}

      <div className="bg-accent/5 border border-accent/20 rounded-lg px-3 py-2">
        <p className="text-xs text-accent/80">Circuit mode — configure exercises performed in sequence, repeated for rounds</p>
      </div>

      {/* Rounds */}
      <div>
        <label className="block text-xs text-white/60 mb-2">Rounds</label>
        <StepperInput value={rounds} onChange={setRounds} min={1} max={20} />
      </div>

      {/* Exercise list */}
      <div>
        <label className="block text-xs text-white/60 mb-2">Exercises (in order)</label>
        <div className="space-y-2">
          {exercises.map((ex, index) => (
            <div key={ex.key} className="rounded-lg border border-secondary-muted/30 bg-secondary-muted/5 p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-white/50 uppercase tracking-wider">
                  #{index + 1}
                </span>
                <div className="flex gap-1">
                  <button
                    type="button"
                    onClick={() => moveExercise(index, 'up')}
                    disabled={index === 0}
                    className="text-white/40 hover:text-white disabled:opacity-20 text-xs px-1"
                  >
                    &#9650;
                  </button>
                  <button
                    type="button"
                    onClick={() => moveExercise(index, 'down')}
                    disabled={index === exercises.length - 1}
                    className="text-white/40 hover:text-white disabled:opacity-20 text-xs px-1"
                  >
                    &#9660;
                  </button>
                  <button
                    type="button"
                    onClick={() => removeExercise(index)}
                    disabled={exercises.length <= 1}
                    className="text-white/40 hover:text-red-400 disabled:opacity-20 text-xs px-1"
                  >
                    &#10005;
                  </button>
                </div>
              </div>

              {/* Exercise name */}
              <div className="mb-2">
                <ExerciseAutocomplete
                  value={ex.exercise_name}
                  onChange={(val) => updateExercise(index, 'exercise_name', val)}
                  onSelect={(item) => handleLibrarySelect(index, item)}
                  categoryFilter="Circuit"
                  placeholder="e.g. Battle Ropes, Box Jumps..."
                />
              </div>

              {/* Duration + Rest */}
              <div className="flex items-center gap-3">
                <div>
                  <label className="block text-[10px] text-white/40 mb-1">Work (s)</label>
                  <input
                    type="number"
                    min="1"
                    max="3600"
                    value={ex.duration_seconds}
                    onChange={(e) => updateExercise(index, 'duration_seconds', Number(e.target.value) || 0)}
                    onFocus={selectOnFocus}
                    className="input w-20 text-sm text-center"
                  />
                </div>
                <div>
                  <label className="block text-[10px] text-white/40 mb-1">Transition rest (s)</label>
                  <input
                    type="number"
                    min="0"
                    max="600"
                    value={ex.rest_seconds}
                    onChange={(e) => updateExercise(index, 'rest_seconds', Number(e.target.value) || 0)}
                    onFocus={selectOnFocus}
                    className="input w-20 text-sm text-center"
                  />
                </div>
              </div>
            </div>
          ))}
        </div>

        <button
          type="button"
          onClick={addExercise}
          className="mt-2 text-sm text-accent hover:text-accent/80 transition-colors"
        >
          + Add Exercise to Circuit
        </button>
      </div>

      {/* Round rest */}
      <div>
        <label className="block text-xs text-white/60 mb-1">Rest between rounds (s)</label>
        <input
          type="number"
          min="0"
          max="600"
          value={roundRest}
          onChange={(e) => setRoundRest(Number(e.target.value) || 0)}
          onFocus={selectOnFocus}
          className="input w-24 text-sm text-center"
          placeholder="60"
        />
      </div>

      {/* Summary */}
      <div className="text-xs text-white/40">
        {exercises.filter(ex => ex.exercise_name.trim()).length} exercises x {rounds} rounds = {exercises.filter(ex => ex.exercise_name.trim()).length * rounds} total intervals
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
          {saving ? 'Saving...' : isEditMode ? 'Update Circuit' : 'Save Circuit'}
        </button>
      </div>
    </form>
  );
}
