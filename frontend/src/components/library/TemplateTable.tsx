'use client';

import { useState, useEffect, useCallback } from 'react';
import { sessionTemplatesApi, exercisesApi } from '@/lib/api';
import { TemplateFormModal } from './TemplateFormModal';
import type { SessionTemplate, ExercisePrescription } from '@/lib/types';

export function TemplateTable() {
  const [templates, setTemplates] = useState<SessionTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<SessionTemplate | null>(null);

  const loadTemplates = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await sessionTemplatesApi.list();
      setTemplates(data);
    } catch (err) {
      setError('Failed to load templates');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  async function handleDelete(id: string) {
    if (!window.confirm('Delete this template?')) return;
    try {
      await sessionTemplatesApi.delete(id);
      setTemplates((prev) => prev.filter((t) => t.id !== id));
    } catch (err) {
      console.error('Failed to delete template:', err);
    }
  }

  return (
    <div>
      {/* Add Button */}
      <div className="flex justify-end mb-4">
        <button
          onClick={() => { setEditingTemplate(null); setShowForm(true); }}
          className="px-3 py-2.5 min-h-[44px] rounded text-sm font-medium bg-accent text-[#090A3D] hover:bg-accent/80 active:bg-accent/70 transition-colors"
        >
          + Create Template
        </button>
      </div>

      {loading ? (
        <div className="text-center py-8">
          <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
      ) : error ? (
        <p className="text-red-400 text-sm py-4 text-center">{error}</p>
      ) : templates.length === 0 ? (
        <p className="text-white/60 text-sm py-8 text-center">
          No templates yet. Create a template to save and reuse exercise plans.
        </p>
      ) : (
        <div className="space-y-3">
          {templates.map((t) => (
            <div
              key={t.id}
              className="border border-secondary-muted rounded-lg p-4 hover:border-accent/30 transition-colors"
            >
              <div className="flex items-center justify-between mb-2">
                <div>
                  <h3 className="font-medium text-sm">{t.template_name}</h3>
                  <p className="text-xs text-white/40">
                    {t.training_type} &middot; {t.exercises.length} exercise{t.exercises.length !== 1 ? 's' : ''}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => { setEditingTemplate(t); setShowForm(true); }}
                    className="text-white/60 hover:text-accent active:text-accent/80 text-xs p-2.5 min-h-[44px] min-w-[44px] inline-flex items-center justify-center transition-colors"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(t.id)}
                    className="text-white/60 hover:text-red-400 active:text-red-300 text-xs p-2.5 min-h-[44px] min-w-[44px] inline-flex items-center justify-center transition-colors"
                  >
                    Delete
                  </button>
                </div>
              </div>

              {t.exercises.length > 0 && (
                <div className="text-xs text-white/50 space-y-0.5">
                  {t.exercises.map((ex) => (
                    <div key={ex.id} className="flex gap-2">
                      <span className="font-medium text-white/70">{ex.exercise_name}</span>
                      <span>
                        {ex.sets}x{ex.reps ?? '?'}
                        {ex.weight_kg ? ` @ ${ex.weight_kg}kg` : ''}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {t.notes && (
                <p className="text-xs text-white/30 mt-2">{t.notes}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {showForm && (
        <TemplateFormModal
          existingTemplate={editingTemplate}
          onClose={() => { setShowForm(false); setEditingTemplate(null); }}
          onSaved={() => {
            setShowForm(false);
            setEditingTemplate(null);
            loadTemplates();
          }}
        />
      )}
    </div>
  );
}
