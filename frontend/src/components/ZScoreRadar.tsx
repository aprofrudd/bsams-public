'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { analysisApi, eventsApi } from '@/lib/api';
import { getMetricLabel } from './MetricSelector';
import type { ReferenceGroup, PerformanceEvent, BenchmarkSource } from '@/lib/types';

interface ZScoreRadarProps {
  athleteId: string;
  referenceGroup: ReferenceGroup;
  benchmarkSource?: BenchmarkSource;
  metricFilter?: string[];
}

interface RadarDataPoint {
  metric: string;
  label: string;
  zScore: number;
  fullMark: 3;
  sourceDate?: string;
  isOverride?: boolean;
  // Zone band values
  zoneOuter: 3;
  zoneMid1: 1;
  zoneMid2: 0;
  zoneInner: -1;
}

const EXCLUDED_KEYS = new Set(['test_type', 'body_mass_kg']);

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: '2-digit',
  });
}

function getZColor(z: number): string {
  if (z >= 1) return '#4ade80';
  if (z >= 0) return '#33CBF4';
  if (z >= -1) return '#facc15';
  return '#f87171';
}

export function ZScoreRadar({ athleteId, referenceGroup, benchmarkSource, metricFilter }: ZScoreRadarProps) {
  const [events, setEvents] = useState<PerformanceEvent[]>([]);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [metricOverrides, setMetricOverrides] = useState<Record<string, string>>({});
  const [allMetricKeys, setAllMetricKeys] = useState<string[]>([]);
  const [metricAvailability, setMetricAvailability] = useState<
    Record<string, { eventId: string; eventDate: string }[]>
  >({});
  const [data, setData] = useState<RadarDataPoint[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingZScores, setIsLoadingZScores] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Effect 1: Fetch events and build metric availability
  useEffect(() => {
    let cancelled = false;

    async function fetchEvents() {
      try {
        setIsLoading(true);
        setError(null);
        const fetchedEvents = await eventsApi.listForAthlete(athleteId);

        if (cancelled) return;

        // Sort newest first
        const sorted = [...fetchedEvents].sort(
          (a, b) => new Date(b.event_date).getTime() - new Date(a.event_date).getTime()
        );

        setEvents(sorted);

        // Build allMetricKeys (union across all events)
        const keySet = new Set<string>();
        for (const evt of sorted) {
          for (const key of Object.keys(evt.metrics)) {
            if (!EXCLUDED_KEYS.has(key) && evt.metrics[key] != null) {
              keySet.add(key);
            }
          }
        }
        const keys = Array.from(keySet);
        const filteredKeys = metricFilter
          ? keys.filter(k => metricFilter.includes(k))
          : keys;
        setAllMetricKeys(filteredKeys);

        // Build metricAvailability
        const availability: Record<string, { eventId: string; eventDate: string }[]> = {};
        for (const key of filteredKeys) {
          availability[key] = sorted
            .filter((evt) => evt.metrics[key] != null)
            .map((evt) => ({ eventId: evt.id, eventDate: evt.event_date }));
        }
        setMetricAvailability(availability);

        // Default to latest event
        if (sorted.length > 0) {
          setSelectedEventId(sorted[0].id);
        } else {
          setSelectedEventId(null);
        }

        // Reset overrides
        setMetricOverrides({});
      } catch (err) {
        if (!cancelled) {
          setError('Failed to load events');
          console.error(err);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchEvents();
    return () => {
      cancelled = true;
    };
  }, [athleteId, metricFilter]);

  // Derive primary metrics (metrics present in selected event)
  const selectedEvent = events.find((e) => e.id === selectedEventId);
  const primaryMetrics = selectedEvent
    ? Object.keys(selectedEvent.metrics).filter(
        (k) => !EXCLUDED_KEYS.has(k) && selectedEvent.metrics[k] != null
      )
    : [];
  const missingMetrics = allMetricKeys.filter((k) => !primaryMetrics.includes(k));

  // Effect 2: Fetch Z-scores when selection changes
  useEffect(() => {
    if (!selectedEventId || events.length === 0) return;

    // Compute primaryMetrics inside the effect to avoid stale closures
    const currentEvent = events.find((e) => e.id === selectedEventId);
    if (!currentEvent) return;

    let currentPrimaryMetrics = Object.keys(currentEvent.metrics).filter(
      (k) => !EXCLUDED_KEYS.has(k) && currentEvent.metrics[k] != null
    );
    if (metricFilter) {
      currentPrimaryMetrics = currentPrimaryMetrics.filter(k => metricFilter.includes(k));
    }

    let cancelled = false;

    async function fetchZScores() {
      setIsLoadingZScores(true);

      try {
        // Build per-metric eventId map
        const metricEventMap: Record<string, { eventId: string; date: string; isOverride: boolean }> = {};
        for (const key of currentPrimaryMetrics) {
          metricEventMap[key] = {
            eventId: selectedEventId!,
            date: currentEvent!.event_date,
            isOverride: false,
          };
        }
        for (const [key, overrideEventId] of Object.entries(metricOverrides)) {
          if (overrideEventId === 'skip') continue;
          const overrideEvent = events.find((e) => e.id === overrideEventId);
          if (overrideEvent) {
            metricEventMap[key] = {
              eventId: overrideEventId,
              date: overrideEvent.event_date,
              isOverride: true,
            };
          }
        }

        // Fetch Z-scores in parallel
        const promises = Object.entries(metricEventMap).map(([metric, info]) =>
          analysisApi
            .getZScore(athleteId, {
              metric,
              referenceGroup,
              eventId: info.eventId,
              benchmarkSource,
            })
            .then((result) => ({
              metric,
              zScore: result.z_score,
              sourceDate: info.date,
              isOverride: info.isOverride,
            }))
            .catch(() => null)
        );

        const results = await Promise.all(promises);

        if (cancelled) return;

        const radarData: RadarDataPoint[] = results
          .filter(
            (r): r is { metric: string; zScore: number; sourceDate: string; isOverride: boolean } =>
              r !== null
          )
          .map((r) => ({
            metric: r.metric,
            label: getMetricLabel(r.metric),
            zScore: r.zScore,
            fullMark: 3 as const,
            sourceDate: r.sourceDate,
            isOverride: r.isOverride,
            zoneOuter: 3 as const,
            zoneMid1: 1 as const,
            zoneMid2: 0 as const,
            zoneInner: -1 as const,
          }));

        setData(radarData);
      } catch (err) {
        if (!cancelled) {
          console.error(err);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingZScores(false);
        }
      }
    }

    fetchZScores();
    return () => {
      cancelled = true;
    };
  }, [selectedEventId, metricOverrides, referenceGroup, benchmarkSource, athleteId, events.length]);

  const handleDateChange = useCallback((eventId: string) => {
    setSelectedEventId(eventId);
    setMetricOverrides({});
  }, []);

  const handleOverrideChange = useCallback((metric: string, eventId: string) => {
    setMetricOverrides((prev) => {
      const next = { ...prev };
      if (eventId === 'skip' || eventId === '') {
        delete next[metric];
      } else {
        next[metric] = eventId;
      }
      return next;
    });
  }, []);

  if (isLoading) {
    return (
      <div className="text-center py-8">
        <div className="inline-block w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        <p className="mt-2 text-white/60">Loading radar chart...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-400">{error}</p>
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-white/60">No events found for this athlete</p>
      </div>
    );
  }

  return (
    <div>
      <h3 className="text-white font-medium mb-4">Z-Score Profile</h3>

      {/* Date Selector */}
      <div className="mb-4">
        <label className="block text-white/60 text-sm mb-1">Event Date</label>
        <select
          value={selectedEventId || ''}
          onChange={(e) => handleDateChange(e.target.value)}
          className="select w-full"
        >
          {events.map((evt, i) => (
            <option key={evt.id} value={evt.id}>
              {formatDate(evt.event_date)}
              {i === 0 ? ' (latest)' : ''}
            </option>
          ))}
        </select>
      </div>

      {/* Composite Metric Picker — only shown when there are missing metrics */}
      {missingMetrics.length > 0 && (
        <div className="mb-4 p-3 rounded-lg bg-white/5 border border-[#2D5585]">
          <p className="text-white/60 text-sm mb-2">
            Missing from selected date — pick an alternate source or skip:
          </p>
          <div className="space-y-2">
            {missingMetrics.map((metricKey) => {
              const available = metricAvailability[metricKey] || [];
              return (
                <div key={metricKey} className="flex items-center gap-2">
                  <span className="text-white/80 text-sm min-w-[140px]">
                    {getMetricLabel(metricKey)}
                  </span>
                  <select
                    className="select flex-1 text-sm"
                    value={metricOverrides[metricKey] || ''}
                    onChange={(e) => handleOverrideChange(metricKey, e.target.value)}
                  >
                    <option value="">Skip</option>
                    {available.map((opt) => (
                      <option key={opt.eventId} value={opt.eventId}>
                        {formatDate(opt.eventDate)}
                      </option>
                    ))}
                  </select>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Vertical Legend */}
      <div className="flex flex-col gap-2 mb-4 text-sm">
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded-full bg-green-400" />
          <span className="text-white/60">Above average (Z &ge; 1)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded-full bg-[#33CBF4]" />
          <span className="text-white/60">Average (0 to 1)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded-full bg-yellow-400" />
          <span className="text-white/60">Below average (-1 to 0)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded-full bg-red-400" />
          <span className="text-white/60">Well below (Z &lt; -1)</span>
        </div>
      </div>

      {/* Loading indicator for Z-scores */}
      {isLoadingZScores && (
        <div className="text-center py-4">
          <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* Radar chart or not enough metrics message */}
      {!isLoadingZScores && data.length < 3 ? (
        <div className="text-center py-8">
          <p className="text-white/60">
            Need at least 3 metrics for radar chart ({data.length} available)
          </p>
        </div>
      ) : (
        !isLoadingZScores && (
          <div className="h-[350px] sm:h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={data} outerRadius="80%">
                {/* Zone band radars — render before PolarGrid for background layering */}
                <Radar
                  dataKey="zoneOuter"
                  stroke="none"
                  fill="#4ade80"
                  fillOpacity={0.06}
                  dot={false}
                  activeDot={false}
                  isAnimationActive={false}
                />
                <Radar
                  dataKey="zoneMid1"
                  stroke="none"
                  fill="#33CBF4"
                  fillOpacity={0.08}
                  dot={false}
                  activeDot={false}
                  isAnimationActive={false}
                />
                <Radar
                  dataKey="zoneMid2"
                  stroke="none"
                  fill="#facc15"
                  fillOpacity={0.10}
                  dot={false}
                  activeDot={false}
                  isAnimationActive={false}
                />
                <Radar
                  dataKey="zoneInner"
                  stroke="none"
                  fill="#f87171"
                  fillOpacity={0.12}
                  dot={false}
                  activeDot={false}
                  isAnimationActive={false}
                />

                <PolarGrid stroke="#2D5585" />
                <PolarAngleAxis
                  dataKey="label"
                  tick={{ fill: '#ffffff99', fontSize: 11 }}
                />
                <PolarRadiusAxis
                  domain={[-3, 3]}
                  tick={{ fill: '#ffffff66', fontSize: 10 }}
                  tickCount={7}
                  axisLine={false}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#07083D',
                    border: '1px solid #2D5585',
                    borderRadius: '8px',
                  }}
                  formatter={(value: number, _name: string, props: any) => {
                    const payload = props?.payload;
                    const z = typeof value === 'number' ? value : payload?.zScore;
                    if (z == null) return ['-', 'Z-Score'];
                    const formatted = `${z >= 0 ? '+' : ''}${z.toFixed(2)}`;
                    if (payload?.isOverride && payload?.sourceDate) {
                      return [`${formatted} (from ${formatDate(payload.sourceDate)})`, 'Z-Score'];
                    }
                    return [formatted, 'Z-Score'];
                  }}
                  labelStyle={{ color: '#ffffff99' }}
                  // Only show tooltip for the zScore dataKey
                  itemStyle={{ display: 'none' }}
                  content={({ active, payload, label }: any) => {
                    if (!active || !payload || payload.length === 0) return null;
                    // Find the zScore entry
                    const zEntry = payload.find((p: any) => p.dataKey === 'zScore');
                    if (!zEntry) return null;
                    const z = zEntry.value as number;
                    const dp = zEntry.payload as RadarDataPoint;
                    const formatted = `${z >= 0 ? '+' : ''}${z.toFixed(2)}`;
                    const dateInfo =
                      dp.isOverride && dp.sourceDate
                        ? ` (from ${formatDate(dp.sourceDate)})`
                        : '';
                    return (
                      <div
                        style={{
                          backgroundColor: '#07083D',
                          border: '1px solid #2D5585',
                          borderRadius: '8px',
                          padding: '8px 12px',
                        }}
                      >
                        <p style={{ color: '#ffffff99', marginBottom: 4 }}>{label}</p>
                        <p style={{ color: getZColor(z), fontWeight: 600 }}>
                          Z-Score: {formatted}
                          {dateInfo}
                        </p>
                      </div>
                    );
                  }}
                />
                {/* Main data radar */}
                <Radar
                  name="Z-Score"
                  dataKey="zScore"
                  stroke="#33CBF4"
                  fill="#33CBF4"
                  fillOpacity={0.25}
                  strokeWidth={2}
                  dot={(props: any) => {
                    const { cx, cy, payload, value } = props;
                    // Recharts passes the dataKey value as `value`; fall back to payload.zScore
                    const z = typeof value === 'number' ? value : payload?.zScore;
                    if (z == null || cx == null || cy == null) return <circle r={0} />;
                    const color = getZColor(z);
                    const isOverride = payload?.isOverride;

                    return (
                      <circle
                        key={payload?.metric || `${cx}-${cy}`}
                        cx={cx}
                        cy={cy}
                        r={6}
                        fill={color}
                        stroke="white"
                        strokeWidth={2}
                        strokeDasharray={isOverride ? '3 2' : undefined}
                      />
                    );
                  }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        )
      )}
    </div>
  );
}
