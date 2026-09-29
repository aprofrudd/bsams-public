'use client';

import { useState } from 'react';
import { ExerciseAutocomplete } from '@/components/training/ExerciseAutocomplete';
import { sessionTemplatesApi } from '@/lib/api';
import type { BlockExercise, ExerciseLibraryItem, SessionTemplate } from '@/lib/types';

const TRAINING_TYPES = ['Strength', 'Conditioning', 'Plyometric', 'Circuit', 'Recovery', 'Other'];

interface BlockSessionEditorProps {
  sessionName: string;
  trainingType: string;
  notes: string;
  exercises: BlockExercise[];
  onSessionNameChange: (name: string) => void;
  onTrainingTypeChange: (type: string) => void;
  onNotesChange: (notes: string) => void;
  onExercisesChange: (exercises: BlockExercise[]) => void;
  onSave: () => void;
  onCancel: () => void;
}

export function BlockSessionEditor({
  sessionName,
  trainingType,
  notes,
  exercises,
  onSessionNameChange,
  onTrainingTypeChange,
  onNotesChange,
  onExercisesChange,
  onSave,
  onCancel,
}: BlockSessionEditorProps) {
  const [newExerciseName, setNewExerciseName] = useState('');
  const [showTemplatePicker, setShowTemplatePicker] = useState(false);
  const [templates, setTemplates] = useState<SessionTemplate[]>([]);
  const [loadingTemplates, setLoadingTemplates] = useState(false);

  async function handleFromTemplate() {
    setShowTemplatePicker(!showTemplatePicker);
    if (templates.length === 0 && !loadingTemplates) {
      setLoadingTemplates(true);
      try {
        const data = await sessionTemplatesApi.list();
        setTemplates(data);
      } catch { /* silent */ }
      finally { setLoadingTemplates(false); }
    }
  }

  function importTemplate(template: SessionTemplate) {
    const mapped: BlockExercise[] = template.exercises.map((tex, i) => ({
      exercise_name: tex.exercise_name,
      exercise_category: tex.exercise_category ?? undefined,
      order_index: exercises.length + i + 1,
      sets: tex.sets,
      reps: tex.reps ?? undefined,
      weight_kg: tex.weight_kg ?? undefined,
      rest_seconds: tex.rest_seconds ?? undefined,
      duration_seconds: tex.duration_seconds ?? undefined,
      distance_meters: tex.distance_meters ?? undefined,
      intensity_type: tex.intensity_type ?? undefined,
      intensity_value: tex.intensity_value ?? undefined,
      rest_between_reps_seconds: tex.rest_between_reps_seconds ?? undefined,
      rep_intensity_values: tex.rep_intensity_values ?? undefined,
      notes: tex.notes ?? undefined,
    }));
    onExercisesChange([...exercises, ...mapped]);
    onTrainingTypeChange(template.training_type);
    setShowTemplatePicker(false);
  }

  function handleAddExercise() {
    if (!newExerciseName.trim()) return;
    const newEx: BlockExercise = {
      exercise_name: newExerciseName.trim(),
      order_index: exercises.length + 1,
      sets: 3,
      reps: 5,
    };
    onExercisesChange([...exercises, newEx]);
    setNewExerciseName('');
  }

  function handleSelectFromLibrary(item: ExerciseLibraryItem) {
    const newEx: BlockExercise = {
      exercise_name: item.exercise_name,
      exercise_category: item.exercise_category,
      order_index: exercises.length + 1,
      sets: item.default_set_configs?.length || 3,
      reps: item.default_reps || undefined,
      weight_kg: item.default_weight_kg || undefined,
      rest_seconds: item.default_rest_seconds || undefined,
      duration_seconds: item.default_duration_seconds || undefined,
      intensity_type: item.default_intensity_type || undefined,
      intensity_value: item.default_intensity_value || undefined,
    };
    onExercisesChange([...exercises, newEx]);
    setNewExerciseName('');
  }

  function handleRemoveExercise(index: number) {
    const updated = exercises.filter((_, i) => i !== index)
      .map((ex, i) => ({ ...ex, order_index: i + 1 }));
    onExercisesChange(updated);
  }

  function handleMoveExercise(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= exercises.length) return;
    const updated = [...exercises];
    [updated[index], updated[target]] = [updated[target], updated[index]];
    onExercisesChange(updated.map((ex, i) => ({ ...ex, order_index: i + 1 })));
  }

  function handleExerciseFieldChange(index: number, field: keyof BlockExercise, value: unknown) {
    const updated = exercises.map((ex, i) =>
      i === index ? { ...ex, [field]: value } : ex
    );
    onExercisesChange(updated);
  }

  function handleLoadTypeToggle(index: number) {
    const ex = exercises[index];
    if (ex.percent_1rm != null) {
      // Switch to absolute
      handleExerciseFieldChange(index, 'percent_1rm', null);
    } else {
      // Switch to percentage
      handleExerciseFieldChange(index, 'weight_kg', null);
      handleExerciseFieldChange(index, 'percent_1rm', 75);
    }
  }

  return (
    <div className="space-y-4">
      {/* Session Name + Type */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-white/50 mb-1">Session Name</label>
          <input
            type="text"
            value={sessionName}
            onChange={(e) => onSessionNameChange(e.target.value)}
            className="input-field w-full"
            placeholder="e.g. Strength 1"
          />
        </div>
        <div>
          <label className="block text-xs text-white/50 mb-1">Training Type</label>
          <select
            value={trainingType}
            onChange={(e) => onTrainingTypeChange(e.target.value)}
            className="input-field w-full"
          >
            {TRAINING_TYPES.map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Notes */}
      <div>
        <label className="block text-xs text-white/50 mb-1">Notes</label>
        <textarea
          value={notes}
          onChange={(e) => onNotesChange(e.target.value)}
          className="input-field w-full"
          rows={2}
          placeholder="Optional session notes..."
        />
      </div>

      {/* Exercise List */}
      <div>
        <h4 className="text-xs text-white/50 mb-2">Exercises ({exercises.length})</h4>
        <div className="space-y-3">
          {exercises.map((ex, index) => (
            <div
              key={`ex-${index}`}
              className="border border-secondary-muted rounded-lg p-3"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">{ex.exercise_name}</span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handleMoveExercise(index, -1)}
                    disabled={index === 0}
                    className="p-1 text-white/40 hover:text-white disabled:opacity-20"
                    title="Move up"
                  >
                    &#9650;
                  </button>
                  <button
                    onClick={() => handleMoveExercise(index, 1)}
                    disabled={index === exercises.length - 1}
                    className="p-1 text-white/40 hover:text-white disabled:opacity-20"
                    title="Move down"
                  >
                    &#9660;
                  </button>
                  <button
                    onClick={() => handleRemoveExercise(index)}
                    className="p-1 text-red-400 hover:text-red-300"
                    title="Remove"
                  >
                    &times;
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <div>
                  <label className="block text-[10px] text-white/40 mb-0.5">Sets</label>
                  <input
                    type="number"
                    value={ex.sets}
                    onChange={(e) => handleExerciseFieldChange(index, 'sets', parseInt(e.target.value) || 1)}
                    className="input-field w-full text-sm"
                    min={1}
                    max={20}
                  />
                </div>
                <div>
                  <label className="block text-[10px] text-white/40 mb-0.5">Reps</label>
                  <input
                    type="number"
                    value={ex.reps ?? ''}
                    onChange={(e) => handleExerciseFieldChange(index, 'reps', e.target.value ? parseInt(e.target.value) : null)}
                    className="input-field w-full text-sm"
                    min={1}
                    max={100}
                  />
                </div>

                {/* Load type toggle */}
                <div>
                  <div className="flex items-center justify-between mb-0.5">
                    <label className="text-[10px] text-white/40">
                      {ex.percent_1rm != null ? '% of 1RM' : 'Weight (kg)'}
                    </label>
                    <button
                      onClick={() => handleLoadTypeToggle(index)}
                      className="text-[9px] text-accent hover:text-accent/80"
                    >
                      {ex.percent_1rm != null ? 'Use kg' : 'Use %'}
                    </button>
                  </div>
                  {ex.percent_1rm != null ? (
                    <input
                      type="number"
                      value={ex.percent_1rm ?? ''}
                      onChange={(e) => handleExerciseFieldChange(index, 'percent_1rm', e.target.value ? parseFloat(e.target.value) : null)}
                      className="input-field w-full text-sm"
                      min={1}
                      max={100}
                      step={5}
                      placeholder="%"
                    />
                  ) : (
                    <input
                      type="number"
                      value={ex.weight_kg ?? ''}
                      onChange={(e) => handleExerciseFieldChange(index, 'weight_kg', e.target.value ? parseFloat(e.target.value) : null)}
                      className="input-field w-full text-sm"
                      min={0}
                      max={500}
                      step={2.5}
                      placeholder="kg"
                    />
                  )}
                </div>

                <div>
                  <label className="block text-[10px] text-white/40 mb-0.5">Rest (s)</label>
                  <input
                    type="number"
                    value={ex.rest_seconds ?? ''}
                    onChange={(e) => handleExerciseFieldChange(index, 'rest_seconds', e.target.value ? parseInt(e.target.value) : null)}
                    className="input-field w-full text-sm"
                    min={0}
                    max={600}
                  />
                </div>
              </div>

              {/* Conditioning: intensity range fields */}
              {(ex.exercise_category === 'Conditioning' || trainingType === 'Conditioning') && (
                <div className="grid grid-cols-3 gap-2 mt-2">
                  <div>
                    <label className="block text-[10px] text-white/40 mb-0.5">Intensity Type</label>
                    <select
                      value={ex.intensity_type ?? ''}
                      onChange={(e) => handleExerciseFieldChange(index, 'intensity_type', e.target.value || null)}
                      className="input-field w-full text-sm"
                    >
                      <option value="">None</option>
                      <option value="power_watts">Power (W)</option>
                      <option value="speed_kmh">Speed (km/h)</option>
                      <option value="rpe">RPE</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-[10px] text-white/40 mb-0.5">Min</label>
                    <input
                      type="number"
                      value={ex.intensity_min ?? ''}
                      onChange={(e) => handleExerciseFieldChange(index, 'intensity_min', e.target.value ? parseFloat(e.target.value) : null)}
                      className="input-field w-full text-sm"
                      min={0}
                      step={1}
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] text-white/40 mb-0.5">Max</label>
                    <input
                      type="number"
                      value={ex.intensity_max ?? ''}
                      onChange={(e) => handleExerciseFieldChange(index, 'intensity_max', e.target.value ? parseFloat(e.target.value) : null)}
                      className="input-field w-full text-sm"
                      min={0}
                      step={1}
                    />
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Add Exercise */}
        <div className="mt-3">
          <div className="flex items-center justify-between mb-1">
            <label className="text-[10px] text-white/40">Add Exercise</label>
            <button
              type="button"
              onClick={handleFromTemplate}
              className="text-xs text-accent hover:text-accent/80 transition-colors"
            >
              From Template
            </button>
          </div>

          {showTemplatePicker && (
            <div className="mb-2 border border-secondary-muted rounded-lg overflow-hidden">
              {loadingTemplates ? (
                <div className="px-3 py-2 text-xs text-white/50">Loading templates...</div>
              ) : templates.length === 0 ? (
                <div className="px-3 py-2 text-xs text-white/50">No templates found</div>
              ) : (
                <div className="max-h-48 overflow-y-auto">
                  {templates.map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => importTemplate(t)}
                      className="w-full text-left px-3 py-2.5 min-h-[44px] text-sm text-white/80 hover:bg-white/5 active:bg-accent/20 transition-colors border-b border-secondary-muted/30 last:border-b-0"
                    >
                      <span className="font-medium">{t.template_name}</span>
                      <span className="text-white/40 ml-2 text-xs">
                        {t.training_type} &middot; {t.exercises.length} exercise{t.exercises.length !== 1 ? 's' : ''}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          <ExerciseAutocomplete
            value={newExerciseName}
            onChange={setNewExerciseName}
            onSelect={handleSelectFromLibrary}
            placeholder="Search exercise library..."
          />
          {newExerciseName.trim() && (
            <button
              onClick={handleAddExercise}
              className="mt-1 text-xs text-accent hover:text-accent/80"
            >
              + Add &quot;{newExerciseName.trim()}&quot; as custom exercise
            </button>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-2 pt-2 border-t border-secondary-muted">
        <button
          onClick={onCancel}
          className="px-4 py-2 min-h-[44px] rounded text-sm font-medium bg-white/5 text-white/60 hover:bg-white/10 transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={onSave}
          disabled={!sessionName.trim()}
          className="px-4 py-2 min-h-[44px] rounded text-sm font-medium bg-accent text-[#090A3D] hover:bg-accent/80 transition-colors disabled:opacity-50"
        >
          Save Session
        </button>
      </div>
    </div>
  );
}
