'use client';

import { useState, useEffect, useCallback } from 'react';
import { eventsApi, airBikeApi } from '@/lib/api';
import { METRIC_BY_KEY } from '@/lib/metricRegistry';
import type { PerformanceEvent, AirBikeTestListItem } from '@/lib/types';

interface TestResultsSummaryProps {
  athleteId: string;
}

interface ResultCard {
  label: string;
  value: number | null;
  previousValue: number | null;
  unit: string;
  date: string | null;
  higherIsBetter: boolean;
}

function getDeltaInfo(current: number, previous: number, higherIsBetter: boolean) {
  const diff = current - previous;
  const pctChange = previous !== 0 ? Math.abs((diff / previous) * 100) : 0;
  const improved = higherIsBetter ? diff > 0 : diff < 0;
  return { improved, pctChange };
}

function formatDate(iso: string): string {
  return new Date(iso + 'T00:00:00').toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

export function TestResultsSummary({ athleteId }: TestResultsSummaryProps) {
  const [cards, setCards] = useState<ResultCard[]>([]);
  const [loading, setLoading] = useState(true);

  const loadResults = useCallback(async () => {
    try {
      setLoading(true);

      const [events, airBikeTests] = await Promise.all([
        eventsApi.listForAthlete(athleteId).catch(() => [] as PerformanceEvent[]),
        airBikeApi.listTests(athleteId).catch(() => [] as AirBikeTestListItem[]),
      ]);

      const results: ResultCard[] = [];

      // CMJ Height — find latest event with height_cm
      const cmjEvents = events
        .filter((e) => e.metrics.height_cm != null)
        .sort((a, b) => b.event_date.localeCompare(a.event_date));
      const cmjDef = METRIC_BY_KEY['height_cm'];
      results.push({
        label: 'CMJ Height',
        value: cmjEvents.length > 0 ? Number(cmjEvents[0].metrics.height_cm) : null,
        previousValue: cmjEvents.length > 1 ? Number(cmjEvents[1].metrics.height_cm) : null,
        unit: 'cm',
        date: cmjEvents.length > 0 ? cmjEvents[0].event_date : null,
        higherIsBetter: cmjDef?.higherIsBetter ?? true,
      });

      // Air Bike Peak Power — latest test max power
      const abSorted = [...airBikeTests].sort((a, b) => b.test_date.localeCompare(a.test_date));
      results.push({
        label: 'Peak Power',
        value: abSorted.length > 0 ? abSorted[0].max_power_w : null,
        previousValue: abSorted.length > 1 ? abSorted[1].max_power_w : null,
        unit: 'W',
        date: abSorted.length > 0 ? abSorted[0].test_date : null,
        higherIsBetter: true,
      });

      setCards(results);
    } catch {
      // Silently handle
    } finally {
      setLoading(false);
    }
  }, [athleteId]);

  useEffect(() => {
    loadResults();
  }, [loadResults]);

  if (loading) {
    return (
      <div className="space-y-2">
        <h3 className="section-title text-sm">Latest Results</h3>
        <div className="flex items-center gap-2 text-white/40 text-sm py-4">
          <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          Loading...
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <h3 className="section-title text-sm">Latest Results</h3>
      <div className="grid grid-cols-2 gap-3">
        {cards.map((card) => (
          <div key={card.label} className="bg-secondary-muted/10 rounded-lg px-3 py-3">
            <div className="text-[10px] text-white/40 uppercase tracking-wider mb-1">{card.label}</div>
            {card.value != null ? (
              <>
                <div className="flex items-baseline gap-1.5">
                  <span className="text-lg font-bold text-white">
                    {Number.isInteger(card.value) ? card.value : card.value.toFixed(1)}
                  </span>
                  <span className="text-xs text-white/40">{card.unit}</span>
                  {card.previousValue != null && (
                    (() => {
                      const { improved, pctChange } = getDeltaInfo(card.value!, card.previousValue, card.higherIsBetter);
                      return (
                        <span className={`text-xs font-medium ${improved ? 'text-green-400' : 'text-red-400'}`}>
                          {improved ? '\u2191' : '\u2193'} {pctChange.toFixed(1)}%
                        </span>
                      );
                    })()
                  )}
                </div>
                <div className="text-[10px] text-white/30 mt-0.5">
                  {card.previousValue == null ? 'First test' : formatDate(card.date!)}
                </div>
              </>
            ) : (
              <div className="text-sm text-white/30 py-1">No data yet</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
