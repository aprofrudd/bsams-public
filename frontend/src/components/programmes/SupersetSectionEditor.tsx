'use client';

import { ExerciseAutocomplete } from '@/components/training/ExerciseAutocomplete';
import type { ProgrammeFormExercise, ProgrammeFormWeek, ExerciseLibraryItem } from '@/lib/types';

interface SupersetSectionEditorProps {
  exercises: ProgrammeFormExercise[];
  onChange: (exercises: ProgrammeFormExercise[]) => void;
  numWeeks: number;
}

function getSlotExercise(exercises: ProgrammeFormExercise[], slot: string): ProgrammeFormExercise | undefined {
  return exercises.find((ex) => ex.slot === slot);
}

function ensureWeeks(weeks: ProgrammeFormWeek[] | undefined, numWeeks: number): ProgrammeFormWeek[] {
  const existing = weeks ?? [];
  const result: ProgrammeFormWeek[] = [];
  for (let i = 0; i < numWeeks; i++) {
    result.push(
      existing[i] ?? {
        week_number: i + 1,
        reps_text: '',
        sets: 3,
        recommended_weight_kg: null,
      }
    );
  }
  return result;
}

export function SupersetSectionEditor({ exercises, onChange, numWeeks }: SupersetSectionEditorProps) {
  const slotA = getSlotExercise(exercises, 'A');
  const slotB = getSlotExercise(exercises, 'B');

  function updateSlot(slot: string, update: Partial<ProgrammeFormExercise>) {
    const existing = exercises.find((ex) => ex.slot === slot);
    if (existing) {
      onChange(
        exercises.map((ex) => (ex.slot === slot ? { ...ex, ...update } : ex))
      );
    } else {
      onChange([
        ...exercises,
        {
          exercise_name: '',
          order_index: exercises.length + 1,
          slot,
          progressive: slot === 'A',
          ...update,
        },
      ]);
    }
  }

  function handleSelectA(item: ExerciseLibraryItem) {
    updateSlot('A', { exercise_name: item.exercise_name });
  }

  function handleSelectB(item: ExerciseLibraryItem) {
    updateSlot('B', { exercise_name: item.exercise_name });
  }

  function handleWeekChange(weekIndex: number, field: keyof ProgrammeFormWeek, value: unknown) {
    const weeks = ensureWeeks(slotA?.weeks, numWeeks);
    const updatedWeeks = weeks.map((w, i) =>
      i === weekIndex ? { ...w, [field]: value } : w
    );
    updateSlot('A', { weeks: updatedWeeks, progressive: true });
  }

  function clearSlot(slot: string) {
    onChange(exercises.filter((ex) => ex.slot !== slot));
  }

  const weeks = ensureWeeks(slotA?.weeks, numWeeks);

  return (
    <div className="space-y-4">
      {/* Slot A - Progressive */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-medium text-accent">A — Progressive</span>
          {slotA && (
            <button
              onClick={() => clearSlot('A')}
              className="text-[10px] text-white/40 hover:text-white/60"
            >
              Clear
            </button>
          )}
        </div>
        <ExerciseAutocomplete
          value={slotA?.exercise_name ?? ''}
          onChange={(v) => updateSlot('A', { exercise_name: v })}
          onSelect={handleSelectA}
          placeholder="Exercise name..."
        />
        {slotA?.exercise_name && (
          <>
            <input
              type="text"
              value={slotA?.notes ?? ''}
              onChange={(e) => updateSlot('A', { notes: e.target.value })}
              className="input-field w-full text-sm mt-2"
              placeholder="Notes (optional)"
            />
            <div className="mt-2 overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-white/50">
                    <th className="text-left p-1 w-16">Week</th>
                    <th className="text-left p-1">Reps</th>
                    <th className="text-left p-1 w-16">Sets</th>
                    <th className="text-left p-1 w-24">Rec. Load</th>
                  </tr>
                </thead>
                <tbody>
                  {weeks.map((w, i) => (
                    <tr key={i}>
                      <td className="p-1 text-white/60">{i + 1}</td>
                      <td className="p-1">
                        <input
                          type="text"
                          value={w.reps_text}
                          onChange={(e) => handleWeekChange(i, 'reps_text', e.target.value)}
                          className="input-field w-full text-xs"
                          placeholder="e.g. 3 x 5"
                        />
                      </td>
                      <td className="p-1">
                        <input
                          type="number"
                          value={w.sets}
                          onChange={(e) => handleWeekChange(i, 'sets', parseInt(e.target.value) || 1)}
                          className="input-field w-full text-xs"
                          min={1}
                          max={20}
                        />
                      </td>
                      <td className="p-1">
                        <input
                          type="number"
                          value={w.recommended_weight_kg ?? ''}
                          onChange={(e) =>
                            handleWeekChange(
                              i,
                              'recommended_weight_kg',
                              e.target.value ? parseFloat(e.target.value) : null
                            )
                          }
                          className="input-field w-full text-xs"
                          placeholder="kg"
                          step={2.5}
                          min={0}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      {/* Slot B - Simple */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-medium text-white/60">B — Simple</span>
          {slotB && (
            <button
              onClick={() => clearSlot('B')}
              className="text-[10px] text-white/40 hover:text-white/60"
            >
              Clear
            </button>
          )}
        </div>
        <ExerciseAutocomplete
          value={slotB?.exercise_name ?? ''}
          onChange={(v) => updateSlot('B', { exercise_name: v })}
          onSelect={handleSelectB}
          placeholder="Exercise name..."
        />
        {slotB?.exercise_name && (
          <input
            type="text"
            value={slotB?.description ?? ''}
            onChange={(e) => updateSlot('B', { description: e.target.value })}
            className="input-field w-full text-sm mt-2"
            placeholder="e.g. 3 x 12 Reps"
          />
        )}
      </div>
    </div>
  );
}
