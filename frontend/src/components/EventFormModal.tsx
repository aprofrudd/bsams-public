'use client';

import { useState, useEffect } from 'react';
import { eventsApi } from '@/lib/api';
import { ResponsiveModal } from '@/components/ResponsiveModal';
import { METRIC_DEFINITIONS } from '@/lib/metricRegistry';
import type { MetricGroup } from '@/lib/metricRegistry';
import type { PerformanceEvent, EventMetrics } from '@/lib/types';

interface EventFormModalProps {
  athleteId: string;
  existingEvent?: PerformanceEvent | null;
  onClose: () => void;
  onSaved: () => void;
  allowedGroups?: MetricGroup[];
}

const FORM_TABS: { group: MetricGroup; label: string }[] = [
  { group: 'jump', label: 'Jump' },
  { group: 'isometric', label: 'Isometric' },
  { group: 'vbt', label: 'VBT' },
  { group: 'mobility', label: 'Mobility' },
];

// Auto-calculated keys — not shown as input fields
const AUTO_CALC_KEYS = new Set(['eur_cm', 'rsi']);

// Group metrics by tab, excluding auto-calculated and metadata
const METRIC_FIELDS_BY_TAB = FORM_TABS.reduce((acc, tab) => {
  acc[tab.group] = METRIC_DEFINITIONS.filter(
    (m) => m.group === tab.group && !AUTO_CALC_KEYS.has(m.key)
  );
  return acc;
}, {} as Record<MetricGroup, typeof METRIC_DEFINITIONS>);

// Body mass is always shown (metadata group)
const BODY_MASS = METRIC_DEFINITIONS.find((m) => m.key === 'body_mass_kg')!;

function toInputDate(isoDate: string): string {
  return isoDate.slice(0, 10);
}

export function EventFormModal({
  athleteId,
  existingEvent,
  onClose,
  onSaved,
  allowedGroups,
}: EventFormModalProps) {
  const isEdit = !!existingEvent;
  const visibleTabs = allowedGroups
    ? FORM_TABS.filter((t) => allowedGroups.includes(t.group))
    : FORM_TABS;
  const [eventDate, setEventDate] = useState(
    existingEvent ? toInputDate(existingEvent.event_date) : ''
  );
  const [metricValues, setMetricValues] = useState<Record<string, string>>({});
  const [activeTab, setActiveTab] = useState<MetricGroup>(visibleTabs[0]?.group ?? 'jump');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (existingEvent) {
      const vals: Record<string, string> = {};
      for (const def of METRIC_DEFINITIONS) {
        const v = existingEvent.metrics[def.key];
        if (v != null) vals[def.key] = String(v);
      }
      setMetricValues(vals);

      // Auto-select tab based on which metrics have values
      for (const tab of visibleTabs) {
        const hasValues = METRIC_FIELDS_BY_TAB[tab.group].some(
          (m) => existingEvent.metrics[m.key] != null
        );
        if (hasValues) {
          setActiveTab(tab.group);
          break;
        }
      }
    }
  }, [existingEvent]);

  function setMetric(key: string, value: string) {
    setMetricValues((prev) => ({ ...prev, [key]: value }));
  }

  function validate(): string | null {
    if (!isEdit && !eventDate) return 'Event date is required';
    // Validate all filled metrics across all tabs
    for (const def of METRIC_DEFINITIONS) {
      const raw = metricValues[def.key];
      if (raw != null && raw !== '' && def.range) {
        const num = Number(raw);
        if (isNaN(num) || num < def.range[0] || num > def.range[1]) {
          return `${def.label} must be ${def.range[0]}–${def.range[1]}`;
        }
      }
    }
    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const metrics: EventMetrics = {};
      for (const def of METRIC_DEFINITIONS) {
        if (AUTO_CALC_KEYS.has(def.key)) continue;
        const raw = metricValues[def.key];
        if (raw != null && raw !== '') {
          metrics[def.key] = Number(raw);
        }
      }

      // Auto-calculate EUR = CMJ - SJ
      if (metrics.height_cm != null && metrics.sj_height_cm != null) {
        metrics.eur_cm = Number((Number(metrics.height_cm) - Number(metrics.sj_height_cm)).toFixed(2));
      }

      // Auto-calculate RSI = Flight Time / Contact Time
      if (metrics.flight_time_ms != null && metrics.contraction_time_ms != null && Number(metrics.contraction_time_ms) !== 0) {
        metrics.rsi = Number((Number(metrics.flight_time_ms) / Number(metrics.contraction_time_ms)).toFixed(2));
      }

      if (isEdit && existingEvent) {
        await eventsApi.update(existingEvent.id, {
          ...(eventDate ? { event_date: eventDate } : {}),
          metrics,
        });
      } else {
        await eventsApi.create({
          athlete_id: athleteId,
          event_date: eventDate,
          metrics,
        });
      }

      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save event');
    } finally {
      setSaving(false);
    }
  }

  const activeFields = METRIC_FIELDS_BY_TAB[activeTab];

  return (
    <ResponsiveModal isOpen={true} onClose={onClose} maxWidth="md" title={isEdit ? 'Edit Data' : 'Add Data'}>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-sm text-white/60 mb-1">Event Date</label>
            <input
              type="date"
              value={eventDate}
              onChange={(e) => setEventDate(e.target.value)}
              className="input w-full"
              required={!isEdit}
            />
          </div>

          {/* Body Mass — always visible */}
          <div>
            <label className="block text-sm text-white/60 mb-1">{BODY_MASS.label}</label>
            <input
              type="number"
              step="any"
              min={BODY_MASS.range?.[0]}
              max={BODY_MASS.range?.[1]}
              value={metricValues[BODY_MASS.key] ?? ''}
              onChange={(e) => setMetric(BODY_MASS.key, e.target.value)}
              className="input w-full"
              placeholder="-"
            />
          </div>

          {/* Test Type Tabs — hidden when scoped to a single group */}
          {visibleTabs.length > 1 && (
            <div className="flex bg-secondary-muted/50 rounded-lg p-1 gap-1">
              {visibleTabs.map((tab) => (
                <button
                  key={tab.group}
                  type="button"
                  onClick={() => setActiveTab(tab.group)}
                  className={`flex-1 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    activeTab === tab.group
                      ? 'bg-accent text-[#090A3D]'
                      : 'text-white/80 hover:text-white hover:bg-secondary-muted/50'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          )}

          {/* Metric Fields for Active Tab */}
          {activeFields.map((def) => (
            <div key={def.key}>
              <label className="block text-sm text-white/60 mb-1">{def.label}</label>
              <input
                type="number"
                step="any"
                min={def.range?.[0]}
                max={def.range?.[1]}
                value={metricValues[def.key] ?? ''}
                onChange={(e) => setMetric(def.key, e.target.value)}
                className="input w-full"
                placeholder="-"
              />
            </div>
          ))}

          {/* Auto-calc hint for Jump tab */}
          {activeTab === 'jump' && (
            <p className="text-xs text-white/40">
              EUR and RSI are auto-calculated from the values above.
            </p>
          )}

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary flex-1"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="btn-primary flex-1 disabled:opacity-50"
            >
              {saving ? 'Saving...' : isEdit ? 'Update' : 'Add'}
            </button>
          </div>
        </form>
    </ResponsiveModal>
  );
}
