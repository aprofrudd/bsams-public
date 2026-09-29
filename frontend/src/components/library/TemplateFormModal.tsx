'use client';

import { useState } from 'react';
import { sessionTemplatesApi } from '@/lib/api';
import { ResponsiveModal } from '@/components/ResponsiveModal';
import { ExerciseAutocomplete } from '@/components/training/ExerciseAutocomplete';
import { TrainingTypeSelector } from '@/components/training/TrainingTypeSelector';
import type { SessionTemplate, TemplateExerciseCreate, ExerciseLibraryItem } from '@/lib/types';

interface TemplateFormModalProps {
  existingTemplate?: SessionTemplate | null;
  onClose: () => void;
  onSaved: () => void;
}

interface ExerciseRow {
  key: number;
  exercise_name: string;
  exercise_category: string;
  exercise_library_id?: string;
  sets: string;
  reps: string;
  weight_kg: string;
  intensity_type: string;
  intensity_value: string;
  rest_between_reps_seconds: string;
  duration_seconds: string;
  rest_seconds: string;
}

let rowKeyCounter = 0;
function nextKey() {
  return ++rowKeyCounter;
}

function createEmptyRow(): ExerciseRow {
  return {
    key: nextKey(),
    exercise_name: '',
    exercise_category: 'Strength',
    sets: '1',
    reps: '',
    weight_kg: '',
    intensity_type: '',
    intensity_value: '',
    rest_between_reps_seconds: '',
    duration_seconds: '',
    rest_seconds: '',
  };
}

export function TemplateFormModal({
  existingTemplate,
  onClose,
  onSaved,
}: TemplateFormModalProps) {
  const isEdit = !!existingTemplate;

  const [templateName, setTemplateName] = useState(existingTemplate?.template_name || '');
  const [trainingType, setTrainingType] = useState(existingTemplate?.training_type || 'Strength');
  const [notes, setNotes] = useState(existingTemplate?.notes || '');
  const [exerciseRows, setExerciseRows] = useState<ExerciseRow[]>(() => {
    if (existingTemplate?.exercises?.length) {
      return existingTemplate.exercises.map((ex) => ({
        key: nextKey(),
        exercise_name: ex.exercise_name,
        exercise_category: ex.exercise_category || 'Strength',
        exercise_library_id: ex.exercise_library_id || undefined,
        sets: String(ex.sets),
        reps: ex.reps ? String(ex.reps) : '',
        weight_kg: ex.weight_kg ? String(ex.weight_kg) : '',
        intensity_type: ex.intensity_type || '',
        intensity_value: ex.intensity_value ? String(ex.intensity_value) : '',
        rest_between_reps_seconds: ex.rest_between_reps_seconds ? String(ex.rest_between_reps_seconds) : '',
        duration_seconds: ex.duration_seconds ? String(ex.duration_seconds) : '',
        rest_seconds: ex.rest_seconds ? String(ex.rest_seconds) : '',
      }));
    }
    return [createEmptyRow()];
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isConditioning = trainingType === 'Conditioning';

  function handleTrainingTypeChange(newType: string) {
    setTrainingType(newType);
    if (newType === 'Conditioning') {
      setExerciseRows((prev) =>
        prev.map((row) => ({ ...row, exercise_category: 'Conditioning' }))
      );
    }
  }

  function updateRow(index: number, field: keyof ExerciseRow, value: string) {
    setExerciseRows((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  }

  function handleLibrarySelect(index: number, item: ExerciseLibraryItem) {
    setExerciseRows((prev) => {
      const updated = [...prev];
      updated[index] = {
        ...updated[index],
        exercise_name: item.exercise_name,
        exercise_category: item.exercise_category || 'Strength',
        exercise_library_id: item.id,
        reps: item.default_reps ? String(item.default_reps) : updated[index].reps,
        weight_kg: item.default_weight_kg ? String(item.default_weight_kg) : updated[index].weight_kg,
        intensity_type: item.default_intensity_type || updated[index].intensity_type,
        intensity_value: item.default_intensity_value ? String(item.default_intensity_value) : updated[index].intensity_value,
        rest_between_reps_seconds: item.default_rest_between_reps_seconds ? String(item.default_rest_between_reps_seconds) : updated[index].rest_between_reps_seconds,
        duration_seconds: item.default_duration_seconds ? String(item.default_duration_seconds) : updated[index].duration_seconds,
        rest_seconds: item.default_rest_seconds ? String(item.default_rest_seconds) : updated[index].rest_seconds,
      };
      return updated;
    });
  }

  function addRow() {
    setExerciseRows((prev) => {
      const row = createEmptyRow();
      if (isConditioning) row.exercise_category = 'Conditioning';
      return [...prev, row];
    });
  }

  function removeRow(index: number) {
    setExerciseRows((prev) => {
      if (prev.length <= 1) return prev;
      return prev.filter((_, i) => i !== index);
    });
  }

  function moveRow(index: number, direction: 'up' | 'down') {
    setExerciseRows((prev) => {
      const newIndex = direction === 'up' ? index - 1 : index + 1;
      if (newIndex < 0 || newIndex >= prev.length) return prev;
      const updated = [...prev];
      [updated[index], updated[newIndex]] = [updated[newIndex], updated[index]];
      return updated;
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!templateName.trim()) {
      setError('Template name is required');
      return;
    }

    // Build exercises list, filtering out empty rows
    const exercises: TemplateExerciseCreate[] = exerciseRows
      .filter((row) => row.exercise_name.trim())
      .map((row, index) => ({
        exercise_library_id: row.exercise_library_id || undefined,
        exercise_name: row.exercise_name.trim(),
        exercise_category: row.exercise_category || undefined,
        order_index: index + 1,
        sets: Number(row.sets) || 1,
        reps: row.reps ? Number(row.reps) : undefined,
        weight_kg: row.weight_kg ? Number(row.weight_kg) : undefined,
        intensity_type: row.intensity_type || undefined,
        intensity_value: row.intensity_value ? Number(row.intensity_value) : undefined,
        rest_between_reps_seconds: row.rest_between_reps_seconds ? Number(row.rest_between_reps_seconds) : undefined,
        duration_seconds: row.duration_seconds ? Number(row.duration_seconds) : undefined,
        rest_seconds: row.rest_seconds ? Number(row.rest_seconds) : undefined,
      }));

    setSaving(true);
    setError(null);

    try {
      if (isEdit && existingTemplate) {
        await sessionTemplatesApi.update(existingTemplate.id, {
          template_name: templateName.trim(),
          training_type: trainingType,
          notes: notes || undefined,
          exercises,
        });
      } else {
        await sessionTemplatesApi.create({
          template_name: templateName.trim(),
          training_type: trainingType,
          notes: notes || undefined,
          exercises,
        });
      }
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save template');
    } finally {
      setSaving(false);
    }
  }

  return (
    <ResponsiveModal isOpen={true} onClose={onClose} maxWidth="3xl" title={isEdit ? 'Edit Template' : 'Create Template'}>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Template Info */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm text-white/60 mb-1">Template Name</label>
              <input
                type="text"
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value)}
                className="input w-full"
                placeholder="e.g. Leg Day"
                required
              />
            </div>
            <div>
              <label className="block text-sm text-white/60 mb-1">Training Type</label>
              <TrainingTypeSelector value={trainingType} onChange={handleTrainingTypeChange} />
            </div>
          </div>

          <div>
            <label className="block text-sm text-white/60 mb-1">Notes (optional)</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="input w-full resize-none"
              rows={2}
              maxLength={1000}
              placeholder="Template description..."
            />
          </div>

          {/* Circuit hint */}
          {trainingType === 'Circuit' && (
            <div className="bg-accent/5 border border-accent/20 rounded-lg px-3 py-2">
              <p className="text-xs text-accent/80">
                Circuit template: &quot;Sets&quot; = number of rounds. All circuit exercises share the same Sets value. Exercises run in sequence each round.
              </p>
            </div>
          )}

          {/* Conditioning hint */}
          {isConditioning && (
            <div className="bg-accent/5 border border-accent/20 rounded-lg px-3 py-2">
              <p className="text-xs text-accent/80">
                Conditioning template: set duration, intensity type &amp; target value, and rest periods for each exercise. Weight is hidden.
              </p>
            </div>
          )}

          {/* Exercises */}
          <div>
            <h3 className="text-sm text-white/60 mb-2">Exercises</h3>
            <div className="space-y-2">
              {exerciseRows.map((row, index) => (
                <div key={row.key} className="border border-secondary-muted/30 rounded-lg p-2 sm:p-0 sm:border-0 sm:rounded-none">
                  {/* Desktop: single-row grid */}
                  {isConditioning ? (
                    <div className="hidden sm:grid grid-cols-[1fr_auto_auto_auto_auto_auto_auto_auto_auto] gap-2 items-end">
                      <div>
                        {index === 0 && <label className="block text-xs text-white/40 mb-1">Name</label>}
                        <ExerciseAutocomplete
                          value={row.exercise_name}
                          onChange={(val) => updateRow(index, 'exercise_name', val)}
                          onSelect={(item) => handleLibrarySelect(index, item)}
                          categoryFilter="Conditioning"
                          placeholder="e.g. HIIT"
                        />
                      </div>
                      <div className="w-14">
                        {index === 0 && <label className="block text-xs text-white/40 mb-1">Sets</label>}
                        <input type="number" min="1" max="20" value={row.sets} onChange={(e) => updateRow(index, 'sets', e.target.value)} className="input w-full text-sm" />
                      </div>
                      <div className="w-14">
                        {index === 0 && <label className="block text-xs text-white/40 mb-1">Reps</label>}
                        <input type="number" min="1" max="100" value={row.reps} onChange={(e) => updateRow(index, 'reps', e.target.value)} className="input w-full text-sm" />
                      </div>
                      <div className="w-16">
                        {index === 0 && <label className="block text-xs text-white/40 mb-1">Dur(s)</label>}
                        <input type="number" min="1" max="600" value={row.duration_seconds} onChange={(e) => updateRow(index, 'duration_seconds', e.target.value)} className="input w-full text-sm" />
                      </div>
                      <div className="w-20">
                        {index === 0 && <label className="block text-xs text-white/40 mb-1">Intensity</label>}
                        <select value={row.intensity_type} onChange={(e) => updateRow(index, 'intensity_type', e.target.value)} className="select w-full text-sm">
                          <option value="">None</option>
                          <option value="rpe">RPE</option>
                          <option value="speed_kmh">km/h</option>
                          <option value="power_watts">W</option>
                        </select>
                      </div>
                      <div className="w-16">
                        {index === 0 && <label className="block text-xs text-white/40 mb-1">Value</label>}
                        <input type="number" step="any" min="0" value={row.intensity_value} onChange={(e) => updateRow(index, 'intensity_value', e.target.value)} className="input w-full text-sm" disabled={!row.intensity_type} />
                      </div>
                      <div className="w-16">
                        {index === 0 && <label className="block text-xs text-white/40 mb-1">Rest</label>}
                        <input type="number" min="0" max="600" value={row.rest_seconds} onChange={(e) => updateRow(index, 'rest_seconds', e.target.value)} className="input w-full text-sm" />
                      </div>
                      <div className="w-16">
                        {index === 0 && <label className="block text-xs text-white/40 mb-1">Rest B/R</label>}
                        <input type="number" min="0" max="600" value={row.rest_between_reps_seconds} onChange={(e) => updateRow(index, 'rest_between_reps_seconds', e.target.value)} className="input w-full text-sm" />
                      </div>
                      <div className="flex gap-1">
                        {index === 0 && <label className="block text-xs text-white/40 mb-1">&nbsp;</label>}
                        <button type="button" onClick={() => moveRow(index, 'up')} disabled={index === 0} className="text-white/40 hover:text-white disabled:opacity-20 text-xs px-1" title="Move up">&#9650;</button>
                        <button type="button" onClick={() => moveRow(index, 'down')} disabled={index === exerciseRows.length - 1} className="text-white/40 hover:text-white disabled:opacity-20 text-xs px-1" title="Move down">&#9660;</button>
                        <button type="button" onClick={() => removeRow(index)} disabled={exerciseRows.length <= 1} className="text-white/40 hover:text-red-400 disabled:opacity-20 text-xs px-1" title="Remove">&#10005;</button>
                      </div>
                    </div>
                  ) : (
                    <div className="hidden sm:grid grid-cols-[1fr_auto_auto_auto_auto_auto_auto_auto] gap-2 items-end">
                      <div>
                        {index === 0 && <label className="block text-xs text-white/40 mb-1">Name</label>}
                        <ExerciseAutocomplete
                          value={row.exercise_name}
                          onChange={(val) => updateRow(index, 'exercise_name', val)}
                          onSelect={(item) => handleLibrarySelect(index, item)}
                        />
                      </div>
                      <div className="w-16">
                        {index === 0 && <label className="block text-xs text-white/40 mb-1">Sets</label>}
                        <input type="number" min="1" max="20" value={row.sets} onChange={(e) => updateRow(index, 'sets', e.target.value)} className="input w-full text-sm" />
                      </div>
                      <div className="w-16">
                        {index === 0 && <label className="block text-xs text-white/40 mb-1">Reps</label>}
                        <input type="number" min="1" max="100" value={row.reps} onChange={(e) => updateRow(index, 'reps', e.target.value)} className="input w-full text-sm" />
                      </div>
                      <div className="w-20">
                        {index === 0 && <label className="block text-xs text-white/40 mb-1">Weight</label>}
                        <input type="number" step="any" min="0" value={row.weight_kg} onChange={(e) => updateRow(index, 'weight_kg', e.target.value)} className="input w-full text-sm" />
                      </div>
                      <div className="w-20">
                        {index === 0 && <label className="block text-xs text-white/40 mb-1">Intensity</label>}
                        <select value={row.intensity_type} onChange={(e) => updateRow(index, 'intensity_type', e.target.value)} className="select w-full text-sm">
                          <option value="">None</option>
                          <option value="rpe">RPE</option>
                          <option value="speed_kmh">km/h</option>
                          <option value="power_watts">W</option>
                        </select>
                      </div>
                      <div className="w-16">
                        {index === 0 && <label className="block text-xs text-white/40 mb-1">Dur(s)</label>}
                        <input type="number" min="1" max="600" value={row.duration_seconds} onChange={(e) => updateRow(index, 'duration_seconds', e.target.value)} className="input w-full text-sm" />
                      </div>
                      <div className="w-16">
                        {index === 0 && <label className="block text-xs text-white/40 mb-1">Rest</label>}
                        <input type="number" min="0" max="600" value={row.rest_seconds} onChange={(e) => updateRow(index, 'rest_seconds', e.target.value)} className="input w-full text-sm" />
                      </div>
                      <div className="flex gap-1">
                        {index === 0 && <label className="block text-xs text-white/40 mb-1">&nbsp;</label>}
                        <button type="button" onClick={() => moveRow(index, 'up')} disabled={index === 0} className="text-white/40 hover:text-white disabled:opacity-20 text-xs px-1" title="Move up">&#9650;</button>
                        <button type="button" onClick={() => moveRow(index, 'down')} disabled={index === exerciseRows.length - 1} className="text-white/40 hover:text-white disabled:opacity-20 text-xs px-1" title="Move down">&#9660;</button>
                        <button type="button" onClick={() => removeRow(index)} disabled={exerciseRows.length <= 1} className="text-white/40 hover:text-red-400 disabled:opacity-20 text-xs px-1" title="Remove">&#10005;</button>
                      </div>
                    </div>
                  )}
                  {/* Mobile: stacked layout */}
                  {isConditioning ? (
                    <div className="sm:hidden space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-white/40">#{index + 1}</span>
                        <div className="flex gap-1">
                          <button type="button" onClick={() => moveRow(index, 'up')} disabled={index === 0} className="text-white/40 hover:text-white disabled:opacity-20 text-xs px-1">&#9650;</button>
                          <button type="button" onClick={() => moveRow(index, 'down')} disabled={index === exerciseRows.length - 1} className="text-white/40 hover:text-white disabled:opacity-20 text-xs px-1">&#9660;</button>
                          <button type="button" onClick={() => removeRow(index)} disabled={exerciseRows.length <= 1} className="text-white/40 hover:text-red-400 disabled:opacity-20 text-xs px-1">&#10005;</button>
                        </div>
                      </div>
                      <ExerciseAutocomplete
                        value={row.exercise_name}
                        onChange={(val) => updateRow(index, 'exercise_name', val)}
                        onSelect={(item) => handleLibrarySelect(index, item)}
                        categoryFilter="Conditioning"
                        placeholder="e.g. HIIT"
                      />
                      <div className="grid grid-cols-3 gap-2">
                        <div>
                          <label className="block text-xs text-white/40 mb-1">Sets</label>
                          <input type="number" min="1" max="20" value={row.sets} onChange={(e) => updateRow(index, 'sets', e.target.value)} className="input w-full text-sm" />
                        </div>
                        <div>
                          <label className="block text-xs text-white/40 mb-1">Reps</label>
                          <input type="number" min="1" max="100" value={row.reps} onChange={(e) => updateRow(index, 'reps', e.target.value)} className="input w-full text-sm" />
                        </div>
                        <div>
                          <label className="block text-xs text-white/40 mb-1">Dur(s)</label>
                          <input type="number" min="1" max="600" value={row.duration_seconds} onChange={(e) => updateRow(index, 'duration_seconds', e.target.value)} className="input w-full text-sm" />
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="block text-xs text-white/40 mb-1">Intensity</label>
                          <select value={row.intensity_type} onChange={(e) => updateRow(index, 'intensity_type', e.target.value)} className="select w-full text-sm">
                            <option value="">None</option>
                            <option value="rpe">RPE</option>
                            <option value="speed_kmh">km/h</option>
                            <option value="power_watts">W</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs text-white/40 mb-1">Value</label>
                          <input type="number" step="any" min="0" value={row.intensity_value} onChange={(e) => updateRow(index, 'intensity_value', e.target.value)} className="input w-full text-sm" disabled={!row.intensity_type} />
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="block text-xs text-white/40 mb-1">Rest (s)</label>
                          <input type="number" min="0" max="600" value={row.rest_seconds} onChange={(e) => updateRow(index, 'rest_seconds', e.target.value)} className="input w-full text-sm" />
                        </div>
                        <div>
                          <label className="block text-xs text-white/40 mb-1">Rest B/R (s)</label>
                          <input type="number" min="0" max="600" value={row.rest_between_reps_seconds} onChange={(e) => updateRow(index, 'rest_between_reps_seconds', e.target.value)} className="input w-full text-sm" />
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="sm:hidden space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-white/40">#{index + 1}</span>
                        <div className="flex gap-1">
                          <button type="button" onClick={() => moveRow(index, 'up')} disabled={index === 0} className="text-white/40 hover:text-white disabled:opacity-20 text-xs px-1">&#9650;</button>
                          <button type="button" onClick={() => moveRow(index, 'down')} disabled={index === exerciseRows.length - 1} className="text-white/40 hover:text-white disabled:opacity-20 text-xs px-1">&#9660;</button>
                          <button type="button" onClick={() => removeRow(index)} disabled={exerciseRows.length <= 1} className="text-white/40 hover:text-red-400 disabled:opacity-20 text-xs px-1">&#10005;</button>
                        </div>
                      </div>
                      <ExerciseAutocomplete
                        value={row.exercise_name}
                        onChange={(val) => updateRow(index, 'exercise_name', val)}
                        onSelect={(item) => handleLibrarySelect(index, item)}
                      />
                      <div className="grid grid-cols-3 gap-2">
                        <div>
                          <label className="block text-xs text-white/40 mb-1">Sets</label>
                          <input type="number" min="1" max="20" value={row.sets} onChange={(e) => updateRow(index, 'sets', e.target.value)} className="input w-full text-sm" />
                        </div>
                        <div>
                          <label className="block text-xs text-white/40 mb-1">Reps</label>
                          <input type="number" min="1" max="100" value={row.reps} onChange={(e) => updateRow(index, 'reps', e.target.value)} className="input w-full text-sm" />
                        </div>
                        <div>
                          <label className="block text-xs text-white/40 mb-1">Weight</label>
                          <input type="number" step="any" min="0" value={row.weight_kg} onChange={(e) => updateRow(index, 'weight_kg', e.target.value)} className="input w-full text-sm" />
                        </div>
                      </div>
                      <div className="grid grid-cols-3 gap-2">
                        <div>
                          <label className="block text-xs text-white/40 mb-1">Intensity</label>
                          <select value={row.intensity_type} onChange={(e) => updateRow(index, 'intensity_type', e.target.value)} className="select w-full text-sm">
                            <option value="">None</option>
                            <option value="rpe">RPE</option>
                            <option value="speed_kmh">km/h</option>
                            <option value="power_watts">W</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs text-white/40 mb-1">Duration (s)</label>
                          <input type="number" min="1" max="600" value={row.duration_seconds} onChange={(e) => updateRow(index, 'duration_seconds', e.target.value)} className="input w-full text-sm" />
                        </div>
                        <div>
                          <label className="block text-xs text-white/40 mb-1">Rest (s)</label>
                          <input type="number" min="0" max="600" value={row.rest_seconds} onChange={(e) => updateRow(index, 'rest_seconds', e.target.value)} className="input w-full text-sm" />
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={addRow}
              className="mt-2 text-sm text-accent hover:text-accent/80 transition-colors"
            >
              + Add Exercise Row
            </button>
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
              {saving ? 'Saving...' : isEdit ? 'Update Template' : 'Create Template'}
            </button>
          </div>
        </form>
    </ResponsiveModal>
  );
}
