'use client';

import { useState } from 'react';
import { ResponsiveModal } from '@/components/ResponsiveModal';
import { programsApi } from '@/lib/api';
import type { ProgramTemplate, ProgramExercise } from '@/lib/types';

interface ProgramTemplateFormModalProps {
  programId: string;
  template: ProgramTemplate | null;
  onClose: () => void;
  onSaved: () => void;
}

const EMPTY_EXERCISE: ProgramExercise = {
  exercise_name: '',
  exercise_category: null,
  order_index: 1,
  sets: 3,
  reps: null,
  weight_kg: null,
  tempo: null,
  rest_seconds: null,
  duration_seconds: null,
  distance_meters: null,
  notes: null,
  intensity_type: null,
  intensity_value: null,
  rest_between_reps_seconds: null,
  rep_intensity_values: null,
};

export function ProgramTemplateFormModal({ programId, template, onClose, onSaved }: ProgramTemplateFormModalProps) {
  const [templateName, setTemplateName] = useState(template?.template_name || '');
  const [trainingType, setTrainingType] = useState(template?.training_type || 'Strength');
  const [orderIndex, setOrderIndex] = useState(template?.order_index || 1);
  const [notes, setNotes] = useState(template?.notes || '');
  const [exercises, setExercises] = useState<ProgramExercise[]>(
    template?.exercises?.length ? template.exercises : [{ ...EMPTY_EXERCISE }]
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function updateExercise(index: number, field: string, value: string | number | null) {
    setExercises(prev => prev.map((ex, i) =>
      i === index ? { ...ex, [field]: value } : ex
    ));
  }

  function addExercise() {
    setExercises(prev => [...prev, { ...EMPTY_EXERCISE, order_index: prev.length + 1 }]);
  }

  function removeExercise(index: number) {
    setExercises(prev => prev.filter((_, i) => i !== index).map((ex, i) => ({ ...ex, order_index: i + 1 })));
  }

  async function handleSave() {
    if (!templateName.trim()) {
      setError('Template name is required');
      return;
    }
    const validExercises = exercises.filter(ex => ex.exercise_name.trim());
    if (validExercises.length === 0) {
      setError('At least one exercise is required');
      return;
    }

    setSaving(true);
    setError(null);

    const data = {
      template_name: templateName.trim(),
      training_type: trainingType,
      order_index: orderIndex,
      notes: notes.trim() || undefined,
      exercises: validExercises.map((ex, i) => ({
        ...ex,
        order_index: i + 1,
        exercise_name: ex.exercise_name.trim(),
      })),
    };

    try {
      if (template) {
        await programsApi.updateTemplate(programId, template.id, data);
      } else {
        await programsApi.addTemplate(programId, data);
      }
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save template');
      setSaving(false);
    }
  }

  return (
    <ResponsiveModal isOpen={true} onClose={onClose} maxWidth="lg" title={template ? 'Edit Template' : 'Add Template'} zIndex={70}>
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm text-white/60 mb-1">Template Name</label>
            <input
              type="text"
              value={templateName}
              onChange={e => setTemplateName(e.target.value)}
              className="w-full px-3 py-2 min-h-[44px] rounded bg-white/5 border border-secondary-muted text-white text-sm focus:outline-none focus:border-accent"
              placeholder="e.g. Week 1 - Upper Body"
            />
          </div>
          <div>
            <label className="block text-sm text-white/60 mb-1">Training Type</label>
            <input
              type="text"
              value={trainingType}
              onChange={e => setTrainingType(e.target.value)}
              className="w-full px-3 py-2 min-h-[44px] rounded bg-white/5 border border-secondary-muted text-white text-sm focus:outline-none focus:border-accent"
              placeholder="e.g. Strength"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm text-white/60 mb-1">Order</label>
            <input
              type="number"
              value={orderIndex}
              onChange={e => setOrderIndex(parseInt(e.target.value) || 1)}
              min={1}
              className="w-full px-3 py-2 min-h-[44px] rounded bg-white/5 border border-secondary-muted text-white text-sm focus:outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="block text-sm text-white/60 mb-1">Notes</label>
            <input
              type="text"
              value={notes}
              onChange={e => setNotes(e.target.value)}
              className="w-full px-3 py-2 min-h-[44px] rounded bg-white/5 border border-secondary-muted text-white text-sm focus:outline-none focus:border-accent"
              placeholder="Optional"
            />
          </div>
        </div>

        {/* Exercises */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm text-white/60">Exercises</label>
            <button
              onClick={addExercise}
              className="text-xs text-accent hover:text-accent/80 transition-colors"
            >
              + Add Exercise
            </button>
          </div>

          <div className="space-y-2 max-h-[40vh] overflow-y-auto">
            {exercises.map((ex, i) => (
              <div key={i} className="border border-secondary-muted/30 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs text-white/30 w-4">{i + 1}.</span>
                  <input
                    type="text"
                    value={ex.exercise_name}
                    onChange={e => updateExercise(i, 'exercise_name', e.target.value)}
                    className="flex-1 px-2 py-1.5 rounded bg-white/5 border border-secondary-muted/50 text-white text-sm focus:outline-none focus:border-accent"
                    placeholder="Exercise name"
                  />
                  {exercises.length > 1 && (
                    <button
                      onClick={() => removeExercise(i)}
                      className="text-red-400/60 hover:text-red-400 transition-colors p-1"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                        <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
                      </svg>
                    </button>
                  )}
                </div>
                <div className="grid grid-cols-4 gap-2">
                  <div>
                    <label className="block text-[10px] text-white/30 mb-0.5">Category</label>
                    <input
                      type="text"
                      value={ex.exercise_category || ''}
                      onChange={e => updateExercise(i, 'exercise_category', e.target.value || null)}
                      className="w-full px-2 py-1 rounded bg-white/5 border border-secondary-muted/50 text-white text-xs focus:outline-none focus:border-accent"
                      placeholder="Strength"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] text-white/30 mb-0.5">Sets</label>
                    <input
                      type="number"
                      value={ex.sets}
                      onChange={e => updateExercise(i, 'sets', parseInt(e.target.value) || 1)}
                      min={1}
                      className="w-full px-2 py-1 rounded bg-white/5 border border-secondary-muted/50 text-white text-xs focus:outline-none focus:border-accent"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] text-white/30 mb-0.5">Reps</label>
                    <input
                      type="number"
                      value={ex.reps ?? ''}
                      onChange={e => updateExercise(i, 'reps', e.target.value ? parseInt(e.target.value) : null)}
                      className="w-full px-2 py-1 rounded bg-white/5 border border-secondary-muted/50 text-white text-xs focus:outline-none focus:border-accent"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] text-white/30 mb-0.5">Weight (kg)</label>
                    <input
                      type="number"
                      value={ex.weight_kg ?? ''}
                      onChange={e => updateExercise(i, 'weight_kg', e.target.value ? parseFloat(e.target.value) : null)}
                      className="w-full px-2 py-1 rounded bg-white/5 border border-secondary-muted/50 text-white text-xs focus:outline-none focus:border-accent"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {error && <p className="text-red-400 text-sm">{error}</p>}

        <button
          onClick={handleSave}
          disabled={saving || !templateName.trim()}
          className="w-full py-2.5 min-h-[44px] rounded text-sm font-medium bg-accent text-[#090A3D] hover:bg-accent/80 active:scale-[0.97] transition-colors disabled:opacity-50"
        >
          {saving ? 'Saving...' : (template ? 'Update Template' : 'Add Template')}
        </button>
      </div>
    </ResponsiveModal>
  );
}
