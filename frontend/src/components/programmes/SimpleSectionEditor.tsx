'use client';

import { ExerciseAutocomplete } from '@/components/training/ExerciseAutocomplete';
import type { ProgrammeFormExercise, ExerciseLibraryItem } from '@/lib/types';

interface SimpleSectionEditorProps {
  exercises: ProgrammeFormExercise[];
  onChange: (exercises: ProgrammeFormExercise[]) => void;
  sectionType: string;
  circuitSets?: number;
  onCircuitSetsChange?: (sets: number) => void;
}

export function SimpleSectionEditor({
  exercises,
  onChange,
  sectionType,
  circuitSets,
  onCircuitSetsChange,
}: SimpleSectionEditorProps) {
  function handleAdd() {
    onChange([
      ...exercises,
      {
        exercise_name: '',
        order_index: exercises.length + 1,
        description: '',
      },
    ]);
  }

  function handleRemove(index: number) {
    const updated = exercises
      .filter((_, i) => i !== index)
      .map((ex, i) => ({ ...ex, order_index: i + 1 }));
    onChange(updated);
  }

  function handleFieldChange(index: number, field: keyof ProgrammeFormExercise, value: unknown) {
    onChange(
      exercises.map((ex, i) => (i === index ? { ...ex, [field]: value } : ex))
    );
  }

  function handleSelectFromLibrary(index: number, item: ExerciseLibraryItem) {
    onChange(
      exercises.map((ex, i) =>
        i === index ? { ...ex, exercise_name: item.exercise_name } : ex
      )
    );
  }

  return (
    <div className="space-y-2">
      {sectionType === 'core_circuit' && onCircuitSetsChange && (
        <div className="flex items-center gap-2 mb-2">
          <label className="text-xs text-white/50">Circuit Sets</label>
          <input
            type="number"
            value={circuitSets ?? 3}
            onChange={(e) => onCircuitSetsChange(Math.max(1, parseInt(e.target.value) || 1))}
            className="input-field w-20 text-sm"
            min={1}
            max={10}
          />
        </div>
      )}

      {exercises.map((ex, index) => (
        <div key={index} className="flex items-start gap-2">
          <div className="flex-1 grid grid-cols-1 sm:grid-cols-[2fr_1fr] gap-2">
            <ExerciseAutocomplete
              value={ex.exercise_name}
              onChange={(v) => handleFieldChange(index, 'exercise_name', v)}
              onSelect={(item) => handleSelectFromLibrary(index, item)}
              placeholder="Exercise name..."
            />
            <input
              type="text"
              value={ex.description ?? ''}
              onChange={(e) => handleFieldChange(index, 'description', e.target.value)}
              className="input-field w-full text-sm"
              placeholder="e.g. 3 x 12 Reps"
            />
          </div>
          <button
            onClick={() => handleRemove(index)}
            className="p-2 text-red-400 hover:text-red-300 mt-1"
            title="Remove"
          >
            &times;
          </button>
        </div>
      ))}

      <button
        onClick={handleAdd}
        className="text-xs text-accent hover:text-accent/80 transition-colors"
      >
        + Add Exercise
      </button>
    </div>
  );
}
