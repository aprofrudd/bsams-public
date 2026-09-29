'use client';

import { useState, useEffect, useCallback } from 'react';
import { wellnessApi } from '@/lib/api';
import type { WellnessEntry } from '@/lib/types';

interface WellnessMiniProps {
  athleteId: string;
  dataVersion: number;
}

function getHiColor(hi: number): string {
  if (hi <= 10) return 'bg-green-400';
  if (hi <= 16) return 'bg-yellow-400';
  return 'bg-red-400';
}

function getDayLabel(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00');
  return date.toLocaleDateString('en-GB', { weekday: 'short' }).slice(0, 3);
}

export function WellnessMini({ athleteId, dataVersion }: WellnessMiniProps) {
  const [entries, setEntries] = useState<WellnessEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const loadEntries = useCallback(async () => {
    try {
      setLoading(true);
      const data = await wellnessApi.listEntries(athleteId);
      // API returns most recent first — take last 7
      setEntries(data.slice(0, 7).reverse());
    } catch {
      // Silently handle
    } finally {
      setLoading(false);
    }
  }, [athleteId]);

  useEffect(() => {
    loadEntries();
  }, [loadEntries, dataVersion]);

  const today = new Date().toISOString().slice(0, 10);

  // Max HI is 28 (7 * 4 fields), min is 4
  const maxHi = 28;

  if (loading) {
    return (
      <div className="space-y-2">
        <h3 className="section-title text-sm">Wellness Trend</h3>
        <div className="flex items-center gap-2 text-white/40 text-sm py-4">
          <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          Loading...
        </div>
      </div>
    );
  }

  if (entries.length === 0) {
    return (
      <div className="space-y-2">
        <h3 className="section-title text-sm">Wellness Trend</h3>
        <div className="bg-secondary-muted/10 rounded-lg px-4 py-6 text-center">
          <p className="text-white/40 text-sm">No wellness data yet. Log your first entry to see your trend.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <h3 className="section-title text-sm">Wellness Trend</h3>
      <div className="bg-secondary-muted/10 rounded-lg px-4 py-4">
        <div className="flex items-end gap-2 h-24">
          {entries.map((entry) => {
            const heightPct = Math.max((entry.hooper_index / maxHi) * 100, 8);
            const isToday = entry.entry_date.slice(0, 10) === today;
            return (
              <div key={entry.id} className="flex-1 flex flex-col items-center gap-1">
                <span className="text-[10px] text-white/50 font-medium">{entry.hooper_index}</span>
                <div className="w-full flex items-end" style={{ height: '64px' }}>
                  <div
                    className={`w-full rounded-t ${getHiColor(entry.hooper_index)} ${isToday ? 'ring-2 ring-white/40' : ''}`}
                    style={{ height: `${heightPct}%`, minHeight: '4px' }}
                  />
                </div>
                <span className={`text-[10px] ${isToday ? 'text-accent font-bold' : 'text-white/40'}`}>
                  {getDayLabel(entry.entry_date)}
                </span>
              </div>
            );
          })}
        </div>
        <div className="flex items-center justify-center gap-4 mt-3 text-[10px] text-white/40">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-green-400" /> Good</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-yellow-400" /> Moderate</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-red-400" /> Poor</span>
        </div>
      </div>
    </div>
  );
}
