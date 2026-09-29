'use client';

import { useState, useEffect, useCallback } from 'react';
import { wellnessApi } from '@/lib/api';
import { WellnessForm } from './WellnessForm';
import type { WellnessEntry } from '@/lib/types';

interface WellnessChartProps {
  athleteId: string;
  onDataChanged?: () => void;
}

const HOOPER_KEYS = [
  { key: 'sleep', label: 'Sleep', color: '#33CBF4' },
  { key: 'fatigue', label: 'Fatigue', color: '#ef4444' },
  { key: 'stress', label: 'Stress', color: '#a855f7' },
  { key: 'doms', label: 'DOMS', color: '#f59e0b' },
];

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
}

function getHooperColor(index: number): string {
  if (index <= 10) return 'text-green-400';
  if (index <= 16) return 'text-yellow-400';
  return 'text-red-400';
}

export function WellnessChart({ athleteId, onDataChanged }: WellnessChartProps) {
  const [entries, setEntries] = useState<WellnessEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingEntry, setEditingEntry] = useState<WellnessEntry | null>(null);

  const loadEntries = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await wellnessApi.listEntries(athleteId);
      setEntries(data);
    } catch (err) {
      setError('Failed to load wellness data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [athleteId]);

  useEffect(() => {
    loadEntries();
  }, [loadEntries]);

  async function handleDelete(entryId: string) {
    if (!window.confirm('Delete this wellness entry?')) return;
    try {
      await wellnessApi.deleteEntry(entryId);
      setEntries((prev) => prev.filter((e) => e.id !== entryId));
      onDataChanged?.();
    } catch (err) {
      console.error('Failed to delete entry:', err);
    }
  }

  // Show entries in chronological order for the chart (newest first in table)
  const sortedEntries = [...entries].sort(
    (a, b) => new Date(a.entry_date).getTime() - new Date(b.entry_date).getTime()
  );
  const recentEntries = sortedEntries.slice(-14); // Last 14 entries for chart

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="section-title text-base">Hooper Index</h3>
        <button
          onClick={() => { setEditingEntry(null); setShowForm(true); }}
          className="px-4 py-2.5 min-h-[44px] rounded text-sm font-medium bg-accent text-[#090A3D] hover:bg-accent/80 active:scale-[0.97] transition-colors"
        >
          + Log Wellness
        </button>
      </div>

      {loading ? (
        <div className="text-center py-8">
          <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
      ) : error ? (
        <p className="text-red-400 text-sm py-4 text-center">{error}</p>
      ) : entries.length === 0 ? (
        <p className="text-white/60 text-sm py-8 text-center">
          No wellness entries logged yet
        </p>
      ) : (
        <>
          {/* Simple bar chart visualization */}
          {recentEntries.length > 0 && (
            <div className="mb-4">
              <div className="flex gap-3 mb-2 flex-wrap">
                {HOOPER_KEYS.map((wk) => (
                  <div key={wk.key} className="flex items-center gap-1">
                    <div
                      className="w-2.5 h-2.5 rounded-full"
                      style={{ backgroundColor: wk.color }}
                    />
                    <span className="text-xs text-white/60">{wk.label}</span>
                  </div>
                ))}
              </div>
              <div className="overflow-x-auto">
                <div className="flex gap-1 min-w-fit">
                  {recentEntries.map((entry) => (
                    <div
                      key={entry.id}
                      className="flex flex-col items-center gap-0.5 cursor-pointer hover:bg-secondary-muted/20 rounded p-1 transition-colors"
                      onClick={() => { setEditingEntry(entry); setShowForm(true); }}
                    >
                      {HOOPER_KEYS.map((wk) => {
                        const val = entry[wk.key as keyof WellnessEntry] as number;
                        return (
                          <div
                            key={wk.key}
                            className="w-8 sm:w-6 rounded-sm"
                            style={{
                              height: `${val * 4}px`,
                              backgroundColor: wk.color,
                              opacity: 0.3 + (val / 7) * 0.7,
                            }}
                            title={`${wk.label}: ${val}/7`}
                          />
                        );
                      })}
                      <span className="text-[10px] text-white/40 mt-1">
                        {formatDate(entry.entry_date)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Table view */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-white/60 border-b border-secondary-muted">
                  <th className="text-left py-2 px-2">Date</th>
                  <th className="text-center py-2 px-1">Sleep</th>
                  <th className="text-center py-2 px-1">Fatigue</th>
                  <th className="text-center py-2 px-1">Stress</th>
                  <th className="text-center py-2 px-1">DOMS</th>
                  <th className="text-center py-2 px-1">HI</th>
                  <th className="text-right py-2 px-2 hidden sm:table-cell">Actions</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr
                    key={entry.id}
                    className="border-b border-secondary-muted/50 hover:bg-secondary-muted/20 transition-colors"
                  >
                    <td className="py-2 px-2 whitespace-nowrap">
                      {formatDate(entry.entry_date)}
                    </td>
                    <td className="py-2 px-1 text-center">{entry.sleep}</td>
                    <td className="py-2 px-1 text-center">{entry.fatigue}</td>
                    <td className="py-2 px-1 text-center">{entry.stress}</td>
                    <td className="py-2 px-1 text-center">{entry.doms}</td>
                    <td className={`py-2 px-1 text-center font-medium ${getHooperColor(entry.hooper_index)}`}>
                      {entry.hooper_index}
                    </td>
                    <td className="py-2 px-2 text-right whitespace-nowrap hidden sm:table-cell">
                      <button
                        onClick={() => { setEditingEntry(entry); setShowForm(true); }}
                        className="min-h-[44px] px-3 py-2 text-sm text-white/60 hover:text-accent active:scale-[0.97] mr-1 transition-colors"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(entry.id)}
                        className="min-h-[44px] px-3 py-2 text-sm text-white/60 hover:text-red-400 active:scale-[0.97] transition-colors"
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
        <WellnessForm
          athleteId={athleteId}
          existingEntry={editingEntry}
          existingDates={entries.map(e => e.entry_date)}
          onClose={() => { setShowForm(false); setEditingEntry(null); }}
          onSaved={() => {
            setShowForm(false);
            setEditingEntry(null);
            loadEntries();
            onDataChanged?.();
          }}
        />
      )}
    </div>
  );
}
