'use client';

import { useState, useEffect } from 'react';
import { trainingBlocksApi } from '@/lib/api';
import type { AthleteMax } from '@/lib/types';

interface AthleteMaxesPanelProps {
  athleteId: string;
  athleteName: string;
}

export function AthleteMaxesPanel({ athleteId, athleteName }: AthleteMaxesPanelProps) {
  const [maxes, setMaxes] = useState<AthleteMax[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [newExercise, setNewExercise] = useState('');
  const [newWeight, setNewWeight] = useState('');
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editWeight, setEditWeight] = useState('');

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const data = await trainingBlocksApi.listAthleteMaxes(athleteId);
        setMaxes(data);
      } catch {
        setError('Failed to load maxes');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [athleteId]);

  async function handleAdd() {
    if (!newExercise.trim() || !newWeight) return;
    setSaving(true);
    setError(null);
    try {
      const result = await trainingBlocksApi.upsertAthleteMax(athleteId, {
        exercise_name: newExercise.trim(),
        max_kg: parseFloat(newWeight),
        source: 'manual',
      });
      setMaxes(prev => {
        const existing = prev.findIndex(m => m.exercise_name === result.exercise_name);
        if (existing >= 0) {
          return prev.map((m, i) => i === existing ? result : m);
        }
        return [...prev, result];
      });
      setNewExercise('');
      setNewWeight('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  }

  async function handleUpdate(exerciseName: string) {
    if (!editWeight) return;
    setSaving(true);
    setError(null);
    try {
      const result = await trainingBlocksApi.upsertAthleteMax(athleteId, {
        exercise_name: exerciseName,
        max_kg: parseFloat(editWeight),
        source: 'manual',
      });
      setMaxes(prev => prev.map(m => m.exercise_name === exerciseName ? result : m));
      setEditingId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(exerciseName: string) {
    try {
      await trainingBlocksApi.deleteAthleteMax(athleteId, exerciseName);
      setMaxes(prev => prev.filter(m => m.exercise_name !== exerciseName));
    } catch {
      setError('Failed to delete');
    }
  }

  return (
    <div className="card max-w-2xl">
      <h3 className="text-sm font-medium mb-3">1RM Maxes — {athleteName}</h3>
      <p className="text-xs text-white/40 mb-4">
        Used for percentage-based loading in training blocks.
      </p>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-sm text-red-400 mb-3">
          {error}
          <button onClick={() => setError(null)} className="ml-2 text-red-300 hover:text-red-200">&times;</button>
        </div>
      )}

      {loading ? (
        <div className="text-center py-6">
          <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
      ) : maxes.length === 0 ? (
        <p className="text-white/40 text-sm text-center py-4">No maxes recorded yet.</p>
      ) : (
        <div className="border border-secondary-muted rounded-lg overflow-hidden mb-4">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-secondary-muted text-white/50 text-xs">
                <th className="text-left p-2">Exercise</th>
                <th className="text-right p-2">1RM (kg)</th>
                <th className="text-left p-2">Source</th>
                <th className="text-right p-2">Updated</th>
                <th className="text-right p-2"></th>
              </tr>
            </thead>
            <tbody>
              {maxes.map(m => (
                <tr key={m.id} className="border-b border-secondary-muted/50">
                  <td className="p-2">{m.exercise_name}</td>
                  <td className="p-2 text-right">
                    {editingId === m.id ? (
                      <input
                        type="number"
                        value={editWeight}
                        onChange={(e) => setEditWeight(e.target.value)}
                        className="input-field w-20 text-sm text-right"
                        min="0"
                        step="0.5"
                        autoFocus
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleUpdate(m.exercise_name);
                          if (e.key === 'Escape') setEditingId(null);
                        }}
                      />
                    ) : (
                      <span>{m.max_kg}</span>
                    )}
                  </td>
                  <td className="p-2">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                      m.source === 'vbt' ? 'bg-cyan-500/10 text-cyan-400' : 'bg-blue-500/10 text-blue-400'
                    }`}>
                      {m.source}
                    </span>
                  </td>
                  <td className="p-2 text-right text-xs text-white/40">
                    {new Date(m.updated_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}
                  </td>
                  <td className="p-2 text-right">
                    {m.source === 'manual' && (
                      <div className="flex items-center justify-end gap-1">
                        {editingId === m.id ? (
                          <>
                            <button
                              onClick={() => handleUpdate(m.exercise_name)}
                              disabled={saving}
                              className="text-[10px] text-green-400 hover:text-green-300"
                            >
                              Save
                            </button>
                            <button
                              onClick={() => setEditingId(null)}
                              className="text-[10px] text-white/40 hover:text-white"
                            >
                              Cancel
                            </button>
                          </>
                        ) : (
                          <>
                            <button
                              onClick={() => { setEditingId(m.id); setEditWeight(String(m.max_kg)); }}
                              className="text-[10px] text-accent hover:text-accent/80"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => handleDelete(m.exercise_name)}
                              className="text-[10px] text-red-400/60 hover:text-red-400"
                            >
                              Delete
                            </button>
                          </>
                        )}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Add new max */}
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <label className="block text-[10px] text-white/40 mb-1">Exercise</label>
          <input
            type="text"
            value={newExercise}
            onChange={(e) => setNewExercise(e.target.value)}
            className="input-field w-full text-sm"
            placeholder="e.g. Back Squat"
          />
        </div>
        <div className="w-24">
          <label className="block text-[10px] text-white/40 mb-1">1RM (kg)</label>
          <input
            type="number"
            value={newWeight}
            onChange={(e) => setNewWeight(e.target.value)}
            className="input-field w-full text-sm"
            min="0"
            step="0.5"
            placeholder="kg"
          />
        </div>
        <button
          onClick={handleAdd}
          disabled={saving || !newExercise.trim() || !newWeight}
          className="px-3 py-2 min-h-[44px] rounded text-xs font-medium bg-accent text-[#090A3D] hover:bg-accent/80 transition-colors disabled:opacity-50"
        >
          Add
        </button>
      </div>
    </div>
  );
}
