'use client';

import { useState, useEffect, useMemo } from 'react';
import { eventsApi, analysisApi } from '@/lib/api';
import { getMetricLabel } from './MetricSelector';
import { EventFormModal } from './EventFormModal';
import type { MetricGroup } from '@/lib/metricRegistry';
import type { ReferenceGroup, PerformanceRow, PerformanceEvent, BenchmarkSource, ZScoreResult } from '@/lib/types';

interface PerformanceTableProps {
  athleteId: string;
  referenceGroup: ReferenceGroup;
  metric: string;
  benchmarkSource?: BenchmarkSource;
  onDataChanged?: () => void;
  allowedGroups?: MetricGroup[];
  readOnly?: boolean;
}

interface ColumnVisibility {
  mass: boolean;
  groupAvg: boolean;
  diff: boolean;
  pctDiff: boolean;
  zScore: boolean;
  percentile: boolean;
  change: boolean;
}

const TOGGLE_COLUMNS: { key: keyof ColumnVisibility; label: string }[] = [
  { key: 'mass', label: 'Mass' },
  { key: 'groupAvg', label: 'Group Avg' },
  { key: 'diff', label: 'Diff' },
  { key: 'pctDiff', label: '% Diff' },
  { key: 'zScore', label: 'Z-Score' },
  { key: 'percentile', label: 'Percentile' },
  { key: 'change', label: 'Change' },
];

export function PerformanceTable({
  athleteId,
  referenceGroup,
  metric,
  benchmarkSource,
  onDataChanged,
  allowedGroups,
  readOnly,
}: PerformanceTableProps) {
  const [rows, setRows] = useState<PerformanceRow[]>([]);
  const [rawEvents, setRawEvents] = useState<PerformanceEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [visibleColumns, setVisibleColumns] = useState<ColumnVisibility>({
    mass: true,
    groupAvg: true,
    diff: true,
    pctDiff: true,
    zScore: true,
    percentile: false,
    change: false,
  });
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingEvent, setEditingEvent] = useState<PerformanceEvent | null>(null);
  const [expandedMobileId, setExpandedMobileId] = useState<string | null>(null);

  // Date filter state
  type DatePreset = '3M' | '6M' | '1Y' | 'All';
  const [datePreset, setDatePreset] = useState<DatePreset>('All');
  const [customFrom, setCustomFrom] = useState('');
  const [customTo, setCustomTo] = useState('');
  const [activeYear, setActiveYear] = useState<number | null>(null);

  // All event dates loaded once (unfiltered) for year extraction
  const [allEventDates, setAllEventDates] = useState<string[]>([]);

  const effectiveDateRange = useMemo((): { startDate?: string; endDate?: string } => {
    if (customFrom || customTo) {
      return {
        ...(customFrom ? { startDate: customFrom } : {}),
        ...(customTo ? { endDate: customTo } : {}),
      };
    }
    if (datePreset !== 'All') {
      const now = new Date();
      const from = new Date(now);
      if (datePreset === '3M') from.setMonth(from.getMonth() - 3);
      else if (datePreset === '6M') from.setMonth(from.getMonth() - 6);
      else if (datePreset === '1Y') from.setFullYear(from.getFullYear() - 1);
      return {
        startDate: from.toISOString().split('T')[0],
        endDate: now.toISOString().split('T')[0],
      };
    }
    return {};
  }, [datePreset, customFrom, customTo]);

  // Load all event dates once on athlete change (unfiltered)
  useEffect(() => {
    eventsApi.listForAthlete(athleteId).then((events) => {
      setAllEventDates(events.map((e) => e.event_date));
    }).catch(() => {});
  }, [athleteId]);

  // Extract unique years from all events
  const availableYears = useMemo(() => {
    const years = new Set(allEventDates.map((d) => new Date(d).getFullYear()));
    return Array.from(years).sort();
  }, [allEventDates]);

  useEffect(() => {
    loadData();
  }, [athleteId, referenceGroup, metric, benchmarkSource, effectiveDateRange]);

  async function loadData(retryCount = 0) {
    try {
      if (retryCount === 0) {
        setIsLoading(true);
        setError(null);
      }

      // Fetch events and bulk Z-scores in parallel
      const [events, zScores] = await Promise.all([
        eventsApi.listForAthlete(athleteId, effectiveDateRange),
        analysisApi.getZScoresBulk(athleteId, {
          metric,
          referenceGroup,
          benchmarkSource,
          ...effectiveDateRange,
        }).catch(() => ({} as Record<string, ZScoreResult>)),
      ]);

      setRawEvents(events);

      const rowsWithZScores: PerformanceRow[] = events.map((event) => {
        const metricValue = event.metrics[metric] != null ? Number(event.metrics[metric]) : null;
        const zResult = zScores[event.id] as ZScoreResult | undefined;

        return {
          id: event.id,
          date: event.event_date,
          bodyMass: event.metrics.body_mass_kg ?? null,
          value: metricValue,
          zScore: zResult?.z_score ?? null,
          groupMean: zResult?.mean ?? null,
          percentileRank: zResult?.percentile_rank ?? null,
          groupStdDev: zResult?.std_dev ?? null,
        };
      });

      setRows(rowsWithZScores);
      setIsLoading(false);
    } catch (err) {
      if (retryCount === 0) {
        console.warn('Performance data load failed, retrying...', err);
        setTimeout(() => loadData(1), 1000);
        return;
      }
      setError('Failed to load performance data');
      console.error('Performance data load failed after retry:', err);
      setIsLoading(false);
    }
  }

  // SWC change calculation
  const changeData = useMemo(() => {
    const sorted = [...rows]
      .filter((r) => r.value !== null)
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

    const map = new Map<string, { change: number; swc: number; meaningful: boolean } | null>();

    for (let i = 0; i < sorted.length; i++) {
      if (i === 0) {
        map.set(sorted[i].id, null);
        continue;
      }
      const prev = sorted[i - 1];
      const curr = sorted[i];
      if (prev.value === null || curr.value === null) {
        map.set(curr.id, null);
        continue;
      }
      const change = curr.value - prev.value;
      const stdDev = curr.groupStdDev ?? prev.groupStdDev;
      const swc = stdDev != null ? 0.2 * stdDev : 0;
      const meaningful = swc > 0 ? Math.abs(change) > swc : false;
      map.set(curr.id, { change, swc, meaningful });
    }

    return map;
  }, [rows]);

  async function handleDelete(eventId: string) {
    if (!window.confirm('Delete this event? This cannot be undone.')) return;
    try {
      await eventsApi.delete(eventId);
      loadData();
      onDataChanged?.();
    } catch {
      setError('Failed to delete event');
    }
  }

  function handleEdit(rowId: string) {
    const event = rawEvents.find((e) => e.id === rowId);
    if (event) setEditingEvent(event);
  }

  function toggleColumn(key: keyof ColumnVisibility) {
    setVisibleColumns((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  const label = getMetricLabel(metric);

  const addEventButton = (
    <button
      onClick={() => setShowAddModal(true)}
      className="px-3 py-2.5 min-h-[44px] rounded-lg text-sm font-medium bg-accent text-[#090A3D] hover:bg-accent/80 active:bg-accent/70 transition-colors"
    >
      + Add Data
    </button>
  );

  if (isLoading) {
    return (
      <div className="text-center py-8">
        <div className="inline-block w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        <p className="mt-2 text-white/60">Loading data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-400">{error}</p>
        <button onClick={() => loadData()} className="btn-secondary mt-4">
          Retry
        </button>
      </div>
    );
  }

  if (rows.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-white/60 mb-4">No performance data recorded</p>
        {!readOnly && addEventButton}
        {!readOnly && showAddModal && (
          <EventFormModal
            athleteId={athleteId}
            onClose={() => setShowAddModal(false)}
            onSaved={() => { setShowAddModal(false); loadData(); onDataChanged?.(); }}
            allowedGroups={allowedGroups}
          />
        )}
      </div>
    );
  }

  const presets: DatePreset[] = ['3M', '6M', '1Y', 'All'];

  function handlePreset(preset: DatePreset) {
    setDatePreset(preset);
    setCustomFrom('');
    setCustomTo('');
    setActiveYear(null);
  }

  function handleCustomFrom(value: string) {
    setCustomFrom(value);
    setDatePreset('All');
    setActiveYear(null);
  }

  function handleCustomTo(value: string) {
    setCustomTo(value);
    setDatePreset('All');
    setActiveYear(null);
  }

  function handleYearPreset(year: number) {
    setActiveYear(year);
    setCustomFrom(`${year}-01-01`);
    setCustomTo(`${year}-12-31`);
    setDatePreset('All');
  }

  return (
    <div className="-mx-4 sm:mx-0">
      {/* Date Filter Controls */}
      <div className="flex flex-wrap items-center gap-3 px-3 sm:px-0 mb-3">
        <div className="flex gap-1">
          {presets.map((p) => (
            <button
              key={p}
              onClick={() => handlePreset(p)}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                datePreset === p && !customFrom && !customTo
                  ? 'bg-accent text-[#090A3D]'
                  : 'bg-[#2D5585]/30 text-white/60 hover:bg-[#2D5585]/50'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
        {/* Year presets */}
        {availableYears.length >= 2 && (
          <>
            <div className="w-px h-5 bg-[#2D5585]/50" />
            <div className="flex gap-1">
              {availableYears.map((year) => (
                <button
                  key={year}
                  onClick={() => handleYearPreset(year)}
                  className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                    activeYear === year
                      ? 'bg-accent text-[#090A3D]'
                      : 'bg-[#2D5585]/30 text-white/60 hover:bg-[#2D5585]/50'
                  }`}
                >
                  {year}
                </button>
              ))}
            </div>
          </>
        )}
        <div className="flex items-center gap-2 text-xs">
          <label className="text-white/40">From</label>
          <input
            type="date"
            value={customFrom}
            onChange={(e) => handleCustomFrom(e.target.value)}
            className="bg-[#07083D] border border-[#2D5585] rounded px-2 py-1 text-white/80 text-xs"
          />
          <label className="text-white/40">To</label>
          <input
            type="date"
            value={customTo}
            onChange={(e) => handleCustomTo(e.target.value)}
            className="bg-[#07083D] border border-[#2D5585] rounded px-2 py-1 text-white/80 text-xs"
          />
        </div>
      </div>

      {/* Column toggles + Add Data */}
      <div className="flex flex-wrap items-center gap-2 px-3 sm:px-0 mb-3">
        {TOGGLE_COLUMNS.map(({ key, label: colLabel }) => (
          <button
            key={key}
            onClick={() => toggleColumn(key)}
            className={`px-3 py-1.5 min-h-[44px] rounded-full text-xs font-medium transition-colors ${
              visibleColumns[key]
                ? 'bg-accent text-primary-bg'
                : 'border border-secondary-muted text-white/40 hover:text-white/60 active:text-white/80'
            }`}
          >
            {colLabel}
          </button>
        ))}
        {!readOnly && (
          <div className="ml-auto">
            {addEventButton}
          </div>
        )}
      </div>

      {/* Mobile card list */}
      <div className="sm:hidden px-3">
        {rows.map((row) => {
          const diff = row.value != null && row.groupMean != null
            ? row.value - row.groupMean
            : null;
          const pctDiff = row.value != null && row.groupMean != null && row.groupMean !== 0
            ? ((row.value - row.groupMean) / row.groupMean) * 100
            : null;
          const isExpanded = expandedMobileId === row.id;
          const chg = changeData.get(row.id);

          return (
            <div
              key={row.id}
              className="bg-[#07083D] border border-[#2D5585] rounded-lg mb-2 p-3"
            >
              <div
                className="flex items-center justify-between cursor-pointer"
                onClick={() => setExpandedMobileId(isExpanded ? null : row.id)}
              >
                <div className="flex items-center gap-3">
                  <span className="text-sm text-white">{formatDate(row.date)}</span>
                  <span className="text-sm font-medium text-[#33CBF4]">
                    {row.value?.toFixed(2) ?? '-'}
                  </span>
                  {visibleColumns.zScore && row.zScore !== null && (
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full bg-white/10 ${getZScoreColor(row.zScore)}`}>
                      {row.zScore >= 0 ? '+' : ''}{row.zScore.toFixed(2)}
                    </span>
                  )}
                </div>
                <span className="text-white/40 text-xs ml-2">
                  {isExpanded ? '\u25B2' : '\u25BC'}
                </span>
              </div>

              {isExpanded && (
                <>
                  <div className="grid grid-cols-2 gap-2 mt-2 pt-2 border-t border-[#2D5585]">
                    {visibleColumns.mass && (
                      <div>
                        <span className="text-xs text-white/40">Mass (kg)</span>
                        <p className="text-sm text-white">{row.bodyMass?.toFixed(1) ?? '-'}</p>
                      </div>
                    )}
                    {visibleColumns.groupAvg && (
                      <div>
                        <span className="text-xs text-white/40">Group Avg</span>
                        <p className="text-sm text-white/60">{row.groupMean?.toFixed(2) ?? '-'}</p>
                      </div>
                    )}
                    {visibleColumns.diff && (
                      <div>
                        <span className="text-xs text-white/40">Diff</span>
                        <p className={`text-sm ${getDiffColor(diff)}`}>
                          {diff != null ? `${diff >= 0 ? '+' : ''}${diff.toFixed(1)}` : '-'}
                        </p>
                      </div>
                    )}
                    {visibleColumns.pctDiff && (
                      <div>
                        <span className="text-xs text-white/40">% Diff</span>
                        <p className={`text-sm ${getDiffColor(pctDiff)}`}>
                          {pctDiff != null ? `${pctDiff >= 0 ? '+' : ''}${pctDiff.toFixed(1)}%` : '-'}
                        </p>
                      </div>
                    )}
                    {visibleColumns.percentile && (
                      <div>
                        <span className="text-xs text-white/40">Percentile</span>
                        <p className={`text-sm ${row.percentileRank != null ? getPercentileColor(row.percentileRank) : 'text-white/60'}`}>
                          {row.percentileRank != null ? `${formatPercentileOrdinal(row.percentileRank)}` : '-'}
                        </p>
                      </div>
                    )}
                    {visibleColumns.change && (
                      <div>
                        <span className="text-xs text-white/40">Change</span>
                        <p className="text-sm">
                          {chg ? (
                            <span className={chg.meaningful ? (chg.change > 0 ? 'text-green-400' : 'text-red-400') : 'text-white/40'}>
                              {chg.meaningful
                                ? `${chg.change > 0 ? '\u2191' : '\u2193'} ${chg.change > 0 ? '+' : ''}${chg.change.toFixed(1)}`
                                : `~ ${Math.abs(chg.change).toFixed(1)}`}
                            </span>
                          ) : '-'}
                        </p>
                      </div>
                    )}
                  </div>

                  {!readOnly && (
                    <div className="flex justify-end gap-2 mt-2 pt-2 border-t border-[#2D5585]">
                      <button
                        onClick={() => handleEdit(row.id)}
                        className="p-2.5 min-h-[44px] min-w-[44px] inline-flex items-center justify-center rounded hover:bg-secondary-muted/50 active:bg-secondary-muted/70 text-white/40 hover:text-accent active:text-accent/80 transition-colors"
                        title="Edit event"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                          <path d="M2.695 14.763l-1.262 3.154a.5.5 0 00.65.65l3.155-1.262a4 4 0 001.343-.885L17.5 5.5a2.121 2.121 0 00-3-3L3.58 13.42a4 4 0 00-.885 1.343z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => handleDelete(row.id)}
                        className="p-2.5 min-h-[44px] min-w-[44px] inline-flex items-center justify-center rounded hover:bg-red-500/20 active:bg-red-500/30 text-white/40 hover:text-red-400 active:text-red-300 transition-colors"
                        title="Delete event"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                          <path fillRule="evenodd" d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z" clipRule="evenodd" />
                        </svg>
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          );
        })}
      </div>

      <div className="hidden sm:block overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-secondary-muted">
              <th className="text-left py-2 sm:py-3 px-3 sm:px-4 text-white/60 font-medium text-sm sm:text-base">
                Date
              </th>
              {visibleColumns.mass && (
                <th className="text-right py-2 sm:py-3 px-3 sm:px-4 text-white/60 font-medium text-sm sm:text-base">
                  Mass (kg)
                </th>
              )}
              <th className="text-right py-2 sm:py-3 px-3 sm:px-4 text-white/60 font-medium text-sm sm:text-base">
                {label}
              </th>
              {visibleColumns.groupAvg && (
                <th className="text-right py-2 sm:py-3 px-3 sm:px-4 text-white/60 font-medium text-sm sm:text-base">
                  Group Avg
                </th>
              )}
              {visibleColumns.diff && (
                <th className="text-right py-2 sm:py-3 px-3 sm:px-4 text-white/60 font-medium text-sm sm:text-base">
                  Diff
                </th>
              )}
              {visibleColumns.pctDiff && (
                <th className="text-right py-2 sm:py-3 px-3 sm:px-4 text-white/60 font-medium text-sm sm:text-base">
                  % Diff
                </th>
              )}
              {visibleColumns.zScore && (
                <th className="text-right py-2 sm:py-3 px-3 sm:px-4 text-white/60 font-medium text-sm sm:text-base">
                  Z-Score
                </th>
              )}
              {visibleColumns.percentile && (
                <th className="text-right py-2 sm:py-3 px-3 sm:px-4 text-white/60 font-medium text-sm sm:text-base">
                  Percentile
                </th>
              )}
              {visibleColumns.change && (
                <th className="text-right py-2 sm:py-3 px-3 sm:px-4 text-white/60 font-medium text-sm sm:text-base">
                  Change
                </th>
              )}
              {!readOnly && <th className="w-20 py-2 sm:py-3 px-2" />}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const diff = row.value != null && row.groupMean != null
                ? row.value - row.groupMean
                : null;
              const pctDiff = row.value != null && row.groupMean != null && row.groupMean !== 0
                ? ((row.value - row.groupMean) / row.groupMean) * 100
                : null;
              const chg = changeData.get(row.id);

              return (
                <tr
                  key={row.id}
                  className="border-b border-secondary-muted/50 hover:bg-secondary-muted/20"
                >
                  <td className="py-2 sm:py-3 px-3 sm:px-4 text-sm sm:text-base">
                    {formatDate(row.date)}
                  </td>
                  {visibleColumns.mass && (
                    <td className="py-2 sm:py-3 px-3 sm:px-4 text-right text-sm sm:text-base">
                      {row.bodyMass?.toFixed(1) ?? '-'}
                    </td>
                  )}
                  <td className="py-2 sm:py-3 px-3 sm:px-4 text-right font-medium text-accent text-sm sm:text-base">
                    {row.value?.toFixed(2) ?? '-'}
                  </td>
                  {visibleColumns.groupAvg && (
                    <td className="py-2 sm:py-3 px-3 sm:px-4 text-right text-sm sm:text-base text-white/60">
                      {row.groupMean?.toFixed(2) ?? '-'}
                    </td>
                  )}
                  {visibleColumns.diff && (
                    <td className={`py-2 sm:py-3 px-3 sm:px-4 text-right text-sm sm:text-base ${getDiffColor(diff)}`}>
                      {diff != null ? `${diff >= 0 ? '+' : ''}${diff.toFixed(1)}` : '-'}
                    </td>
                  )}
                  {visibleColumns.pctDiff && (
                    <td className={`py-2 sm:py-3 px-3 sm:px-4 text-right text-sm sm:text-base ${getDiffColor(pctDiff)}`}>
                      {pctDiff != null ? `${pctDiff >= 0 ? '+' : ''}${pctDiff.toFixed(1)}%` : '-'}
                    </td>
                  )}
                  {visibleColumns.zScore && (
                    <td className="py-2 sm:py-3 px-3 sm:px-4 text-right text-sm sm:text-base">
                      {row.zScore !== null ? (
                        <span className={getZScoreColor(row.zScore)}>
                          {row.zScore >= 0 ? '+' : ''}
                          {row.zScore.toFixed(2)}
                        </span>
                      ) : (
                        '-'
                      )}
                    </td>
                  )}
                  {visibleColumns.percentile && (
                    <td className="py-2 sm:py-3 px-3 sm:px-4 text-right text-sm sm:text-base">
                      {row.percentileRank != null ? (
                        <span className={getPercentileColor(row.percentileRank)}>
                          {formatPercentileOrdinal(row.percentileRank)}
                        </span>
                      ) : (
                        '-'
                      )}
                    </td>
                  )}
                  {visibleColumns.change && (
                    <td className="py-2 sm:py-3 px-3 sm:px-4 text-right text-sm sm:text-base">
                      {chg ? (
                        <span className={chg.meaningful ? (chg.change > 0 ? 'text-green-400' : 'text-red-400') : 'text-white/40'}>
                          {chg.meaningful
                            ? `${chg.change > 0 ? '\u2191' : '\u2193'} ${chg.change > 0 ? '+' : ''}${chg.change.toFixed(1)}`
                            : `~ ${Math.abs(chg.change).toFixed(1)}`}
                        </span>
                      ) : (
                        '-'
                      )}
                    </td>
                  )}
                  {!readOnly && (
                    <td className="py-2 sm:py-3 px-2 text-right whitespace-nowrap">
                      <button
                        onClick={() => handleEdit(row.id)}
                        className="p-2.5 min-h-[44px] min-w-[44px] inline-flex items-center justify-center rounded hover:bg-secondary-muted/50 active:bg-secondary-muted/70 text-white/40 hover:text-accent active:text-accent/80 transition-colors"
                        title="Edit event"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                          <path d="M2.695 14.763l-1.262 3.154a.5.5 0 00.65.65l3.155-1.262a4 4 0 001.343-.885L17.5 5.5a2.121 2.121 0 00-3-3L3.58 13.42a4 4 0 00-.885 1.343z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => handleDelete(row.id)}
                        className="p-2.5 min-h-[44px] min-w-[44px] inline-flex items-center justify-center rounded hover:bg-red-500/20 active:bg-red-500/30 text-white/40 hover:text-red-400 active:text-red-300 transition-colors"
                        title="Delete event"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                          <path fillRule="evenodd" d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z" clipRule="evenodd" />
                        </svg>
                      </button>
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Add Event Modal */}
      {!readOnly && showAddModal && (
        <EventFormModal
          athleteId={athleteId}
          onClose={() => setShowAddModal(false)}
          onSaved={() => { setShowAddModal(false); loadData(); onDataChanged?.(); }}
          allowedGroups={allowedGroups}
        />
      )}

      {/* Edit Event Modal */}
      {!readOnly && editingEvent && (
        <EventFormModal
          athleteId={athleteId}
          existingEvent={editingEvent}
          onClose={() => setEditingEvent(null)}
          onSaved={() => { setEditingEvent(null); loadData(); onDataChanged?.(); }}
          allowedGroups={allowedGroups}
        />
      )}
    </div>
  );
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

function getDiffColor(value: number | null): string {
  if (value == null || value === 0) return 'text-white/60';
  return value > 0 ? 'text-green-400' : 'text-red-400';
}

function getZScoreColor(zScore: number): string {
  if (zScore >= 1) return 'text-green-400';
  if (zScore >= 0) return 'text-accent';
  if (zScore >= -1) return 'text-yellow-400';
  return 'text-red-400';
}

function getPercentileColor(percentile: number): string {
  if (percentile >= 75) return 'text-green-400';
  if (percentile >= 50) return 'text-accent';
  if (percentile >= 25) return 'text-yellow-400';
  return 'text-red-400';
}

function formatPercentileOrdinal(p: number): string {
  const rounded = Math.round(p);
  const suffix =
    rounded % 100 >= 11 && rounded % 100 <= 13
      ? 'th'
      : rounded % 10 === 1
        ? 'st'
        : rounded % 10 === 2
          ? 'nd'
          : rounded % 10 === 3
            ? 'rd'
            : 'th';
  return `${rounded}${suffix}`;
}
