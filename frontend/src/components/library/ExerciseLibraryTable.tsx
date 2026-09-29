'use client';

import { useState, useEffect, useCallback } from 'react';
import { exerciseLibraryApi } from '@/lib/api';
import { ExerciseLibraryFormModal } from './ExerciseLibraryFormModal';
import type { ExerciseLibraryItem } from '@/lib/types';

const EXERCISE_CATEGORIES = ['All', 'Strength', 'Plyometric', 'Conditioning', 'Circuit', 'Other'];

export function ExerciseLibraryTable() {
  const [exercises, setExercises] = useState<ExerciseLibraryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('All');
  const [showForm, setShowForm] = useState(false);
  const [editingExercise, setEditingExercise] = useState<ExerciseLibraryItem | null>(null);
  const [expandedExId, setExpandedExId] = useState<string | null>(null);

  const loadExercises = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const options: { search?: string; category?: string } = {};
      if (searchQuery) options.search = searchQuery;
      if (categoryFilter !== 'All') options.category = categoryFilter;
      const data = await exerciseLibraryApi.list(options);
      setExercises(data);
    } catch (err) {
      setError('Failed to load exercises');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [searchQuery, categoryFilter]);

  useEffect(() => {
    loadExercises();
  }, [loadExercises]);

  async function handleDelete(id: string) {
    if (!window.confirm('Delete this exercise from your library?')) return;
    try {
      await exerciseLibraryApi.delete(id);
      setExercises((prev) => prev.filter((ex) => ex.id !== id));
    } catch (err) {
      console.error('Failed to delete exercise:', err);
    }
  }

  return (
    <div>
      {/* Search and Filter Controls */}
      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <input
          type="text"
          placeholder="Search exercises..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="input flex-1 text-sm"
        />
        <div className="flex gap-1">
          {EXERCISE_CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              className={`px-3 py-2.5 min-h-[44px] rounded text-xs font-medium transition-colors ${
                categoryFilter === cat
                  ? 'bg-accent text-[#090A3D]'
                  : 'bg-secondary-muted/30 text-white/60 hover:text-white active:text-white'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Add Button */}
      <div className="flex justify-end mb-4">
        <button
          onClick={() => { setEditingExercise(null); setShowForm(true); }}
          className="px-3 py-2.5 min-h-[44px] rounded text-sm font-medium bg-accent text-[#090A3D] hover:bg-accent/80 active:bg-accent/70 transition-colors"
        >
          + Add Exercise
        </button>
      </div>

      {loading ? (
        <div className="text-center py-8">
          <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
      ) : error ? (
        <p className="text-red-400 text-sm py-4 text-center">{error}</p>
      ) : exercises.length === 0 ? (
        <p className="text-white/60 text-sm py-8 text-center">
          {searchQuery || categoryFilter !== 'All'
            ? 'No exercises match your search'
            : 'No exercises in your library yet. Add your first exercise to get started.'}
        </p>
      ) : (
        <>
        {/* Mobile card list */}
        <div className="sm:hidden space-y-2">
          {exercises.map((ex) => (
            <div key={ex.id} className="bg-[#07083D] border border-[#2D5585] rounded-lg mb-2 p-3">
              <div
                className="flex items-center justify-between cursor-pointer"
                onClick={() => setExpandedExId(expandedExId === ex.id ? null : ex.id)}
              >
                <div className="flex-1 min-w-0">
                  <span className="text-white text-sm font-medium truncate block">{ex.exercise_name}</span>
                  <span className="text-white/40 text-xs">{ex.exercise_category || 'Uncategorised'}</span>
                </div>
                <div className="flex items-center gap-3 ml-2 shrink-0">
                  <span className="text-white/60 text-xs">{ex.default_reps ?? '-'} reps</span>
                  <span className="text-white/40 text-sm">{expandedExId === ex.id ? '\u25B2' : '\u25BC'}</span>
                </div>
              </div>
              {expandedExId === ex.id && (
                <>
                  <div className="grid grid-cols-2 gap-2 mt-2 pt-2 border-t border-[#2D5585]">
                    <div>
                      <span className="text-white/40 text-xs block">Reps</span>
                      <span className="text-white text-sm">{ex.default_reps ?? '-'}</span>
                    </div>
                    <div>
                      <span className="text-white/40 text-xs block">Weight</span>
                      <span className="text-white text-sm">{ex.default_weight_kg != null ? `${ex.default_weight_kg} kg` : '-'}</span>
                    </div>
                    <div>
                      <span className="text-white/40 text-xs block">Rest</span>
                      <span className="text-white text-sm">{ex.default_rest_seconds != null ? `${ex.default_rest_seconds}s` : '-'}</span>
                    </div>
                    <div>
                      <span className="text-white/40 text-xs block">Notes</span>
                      <span className="text-white text-sm">{ex.notes || '-'}</span>
                    </div>
                  </div>
                  <div className="flex gap-2 mt-3 pt-2 border-t border-[#2D5585]">
                    <button
                      onClick={() => { setEditingExercise(ex); setShowForm(true); }}
                      className="text-accent text-xs px-3 py-2 min-h-[44px] rounded bg-accent/10 hover:bg-accent/20 active:bg-accent/30 transition-colors"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(ex.id)}
                      className="text-red-400 text-xs px-3 py-2 min-h-[44px] rounded bg-red-400/10 hover:bg-red-400/20 active:bg-red-400/30 transition-colors"
                    >
                      Delete
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>

        {/* Desktop table */}
        <div className="hidden sm:block overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-white/60 border-b border-secondary-muted">
                <th className="text-left py-2 px-2">Exercise</th>
                <th className="text-left py-2 px-2">Category</th>
                <th className="text-right py-2 px-2">Reps</th>
                <th className="text-right py-2 px-2">Weight</th>
                <th className="text-left py-2 px-2 hidden md:table-cell">Tempo</th>
                <th className="text-right py-2 px-2 hidden md:table-cell">Rest</th>
                <th className="text-left py-2 px-2 hidden lg:table-cell">Notes</th>
                <th className="text-right py-2 px-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {exercises.map((ex) => (
                <tr
                  key={ex.id}
                  className="border-b border-secondary-muted/50 hover:bg-secondary-muted/20 transition-colors"
                >
                  <td className="py-2 px-2 font-medium">{ex.exercise_name}</td>
                  <td className="py-2 px-2 text-white/60">{ex.exercise_category || '-'}</td>
                  <td className="py-2 px-2 text-right">{ex.default_reps ?? '-'}</td>
                  <td className="py-2 px-2 text-right">
                    {ex.default_weight_kg != null ? `${ex.default_weight_kg} kg` : '-'}
                  </td>
                  <td className="py-2 px-2 text-white/60 hidden md:table-cell">{ex.default_tempo || '-'}</td>
                  <td className="py-2 px-2 text-right hidden md:table-cell">
                    {ex.default_rest_seconds != null ? `${ex.default_rest_seconds}s` : '-'}
                  </td>
                  <td className="py-2 px-2 text-white/60 max-w-[200px] truncate hidden lg:table-cell">
                    {ex.notes || '-'}
                  </td>
                  <td className="py-2 px-2 text-right whitespace-nowrap">
                    <button
                      onClick={() => { setEditingExercise(ex); setShowForm(true); }}
                      className="text-white/60 hover:text-accent active:text-accent/80 text-xs mr-1 p-2.5 min-h-[44px] min-w-[44px] inline-flex items-center justify-center transition-colors"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(ex.id)}
                      className="text-white/60 hover:text-red-400 active:text-red-300 text-xs p-2.5 min-h-[44px] min-w-[44px] inline-flex items-center justify-center transition-colors"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        </>
      )}

      {showForm && (
        <ExerciseLibraryFormModal
          existingExercise={editingExercise}
          presetCategory={!editingExercise && categoryFilter !== 'All' ? categoryFilter : undefined}
          onClose={() => { setShowForm(false); setEditingExercise(null); }}
          onSaved={() => {
            setShowForm(false);
            setEditingExercise(null);
            loadExercises();
          }}
        />
      )}
    </div>
  );
}
