'use client';

import { useMemo, useState } from 'react';
import type { CombineStationRosterEntry } from '@/lib/types';

type Filter = 'todo' | 'all' | 'done';

/**
 * The left third of a station screen: who is still to come.
 *
 * Sorted to-do first, because that is the order the operator works in. Rows are
 * 64px tall so they are hittable on an iPad without looking.
 */
export function ParticipantPicker({
  entries,
  selectedId,
  onSelect,
  done,
  total,
}: {
  entries: CombineStationRosterEntry[];
  selectedId: string | null;
  onSelect: (participantId: string) => void;
  done: number;
  total: number;
}) {
  const [filter, setFilter] = useState<Filter>('todo');
  const [search, setSearch] = useState('');

  const visible = useMemo(() => {
    const query = search.trim().toLowerCase();
    return entries.filter((entry) => {
      // The boxer on screen always stays on the list: their first logged attempt
      // flips them to "done", and dropping them mid-set hides the boxer standing
      // in front of the operator with two jumps left.
      if (entry.participant_id === selectedId) return true;
      if (filter !== 'all' && entry.status !== filter) return false;
      if (!query) return true;
      return (
        entry.name.toLowerCase().includes(query) ||
        String(entry.bib).includes(query) ||
        (entry.club ?? '').toLowerCase().includes(query)
      );
    });
  }, [entries, filter, search, selectedId]);

  const nextUp = entries.filter((e) => e.status === 'todo').slice(0, 3);

  return (
    <div className="flex h-full flex-col gap-3">
      <div>
        <div className="flex items-baseline justify-between">
          <h2 className="section-title text-sm">Roster</h2>
          <span className="font-mono text-sm tabular-nums text-white/50">
            {done} of {total} done
          </span>
        </div>
        <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-secondary-muted/30">
          <div
            className="h-full rounded-full bg-accent transition-all"
            style={{ width: `${total ? (done / total) * 100 : 0}%` }}
          />
        </div>
      </div>

      {nextUp.length > 0 && (
        <div className="rounded-lg border border-accent/30 bg-accent/5 p-3">
          <p className="text-xs uppercase tracking-widest text-accent/70">Next up</p>
          <p className="mt-1 text-lg font-semibold leading-tight text-white">
            {nextUp.map((e) => e.name).join(' · ')}
          </p>
        </div>
      )}

      <div className="flex gap-1">
        {(['todo', 'all', 'done'] as Filter[]).map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => setFilter(option)}
            className={`min-h-[44px] flex-1 rounded-lg text-sm font-medium uppercase tracking-wide transition-all active:scale-[0.97] ${
              filter === option
                ? 'bg-accent text-[#090A3D]'
                : 'bg-secondary-muted/20 text-white/60'
            }`}
          >
            {option === 'todo' ? 'To do' : option}
          </button>
        ))}
      </div>

      <input
        type="search"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search name, bib or club"
        className="input w-full"
      />

      <ul className="min-h-0 flex-1 space-y-1 overflow-y-auto">
        {visible.map((entry) => {
          const isSelected = entry.participant_id === selectedId;
          return (
            <li key={entry.participant_id}>
              <button
                type="button"
                onClick={() => onSelect(entry.participant_id)}
                className={`flex min-h-[64px] w-full items-center gap-3 rounded-lg px-3 text-left transition-all active:scale-[0.99] ${
                  isSelected
                    ? 'bg-accent/20 ring-2 ring-accent'
                    : 'bg-primary-dark hover:bg-secondary-muted/20'
                }`}
              >
                <span className="w-10 shrink-0 font-mono text-lg tabular-nums text-white/40">
                  {entry.bib}
                </span>
                <span className="min-w-0 flex-1">
                  <span
                    className={`block truncate text-base font-semibold ${
                      entry.status === 'done' ? 'text-white/50' : 'text-white'
                    }`}
                  >
                    {entry.name}
                  </span>
                  <span className="block truncate text-xs text-white/40">
                    {[entry.weight_category, entry.club].filter(Boolean).join(' · ') || '—'}
                  </span>
                </span>
                {entry.status === 'done' ? (
                  <span className="shrink-0 text-right">
                    <span className="block font-mono text-sm tabular-nums text-accent">
                      {entry.best_display}
                    </span>
                    <span className="block text-[10px] uppercase tracking-widest text-green-400">
                      {entry.attempt_count} logged
                    </span>
                  </span>
                ) : (
                  <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-amber-400" />
                )}
              </button>
            </li>
          );
        })}
        {visible.length === 0 && (
          <li className="py-8 text-center text-sm text-white/40">
            {filter === 'todo' ? 'Everyone has been through this station.' : 'No matches.'}
          </li>
        )}
      </ul>
    </div>
  );
}
