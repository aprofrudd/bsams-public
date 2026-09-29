'use client';

import { useState, useEffect, useRef } from 'react';
import { analysisApi } from '@/lib/api';
import { getMetricLabel, METRIC_BY_KEY, GROUP_LABELS } from '@/lib/metricRegistry';
import type { MetricGroup } from '@/lib/metricRegistry';

export { getMetricLabel };

interface MetricSelectorProps {
  athleteId: string;
  selectedMetric: string;
  onMetricChange: (metric: string) => void;
  disabled?: boolean;
  dataVersion?: number;
  metricFilter?: string[];
  onMetricsAvailable?: (count: number) => void;
}

const GROUP_ORDER: MetricGroup[] = ['jump', 'vbt', 'mobility', 'isometric'];

export function MetricSelector({
  athleteId,
  selectedMetric,
  onMetricChange,
  disabled = false,
  dataVersion = 0,
  metricFilter,
  onMetricsAvailable,
}: MetricSelectorProps) {
  const [metrics, setMetrics] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const onMetricsAvailableRef = useRef(onMetricsAvailable);
  onMetricsAvailableRef.current = onMetricsAvailable;

  useEffect(() => {
    if (!athleteId) return;

    setIsLoading(true);
    analysisApi
      .getAvailableMetrics(athleteId)
      .then((data) => {
        const filtered = metricFilter
          ? data.filter(k => metricFilter.includes(k))
          : data;
        setMetrics(filtered);
        onMetricsAvailableRef.current?.(filtered.length);
        // If current selection isn't available, select the first metric
        if (filtered.length > 0 && !filtered.includes(selectedMetric)) {
          onMetricChange(filtered[0]);
        }
      })
      .catch(() => {
        setMetrics([]);
        onMetricsAvailableRef.current?.(0);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [athleteId, dataVersion, metricFilter]);

  // Group available metrics by their group
  const grouped = GROUP_ORDER.map((group) => ({
    group,
    label: GROUP_LABELS[group],
    metrics: metrics.filter((key) => METRIC_BY_KEY[key]?.group === group),
  })).filter((g) => g.metrics.length > 0);

  // Metrics not in any known group (legacy/unknown)
  const ungrouped = metrics.filter((key) => {
    const def = METRIC_BY_KEY[key];
    return !def || !GROUP_ORDER.includes(def.group as MetricGroup);
  });

  return (
    <select
      value={selectedMetric}
      onChange={(e) => onMetricChange(e.target.value)}
      disabled={disabled || isLoading || metrics.length === 0}
      className="select w-full"
    >
      {metrics.length === 0 ? (
        <option value="">
          {isLoading ? 'Loading...' : 'No metrics available'}
        </option>
      ) : grouped.length > 1 || ungrouped.length > 0 ? (
        <>
          {grouped.map((g) => (
            <optgroup key={g.group} label={g.label}>
              {g.metrics.map((key) => (
                <option key={key} value={key}>
                  {getMetricLabel(key)}
                </option>
              ))}
            </optgroup>
          ))}
          {ungrouped.length > 0 && (
            <optgroup label="Other">
              {ungrouped.map((key) => (
                <option key={key} value={key}>
                  {getMetricLabel(key)}
                </option>
              ))}
            </optgroup>
          )}
        </>
      ) : (
        // Single group or flat list — no need for optgroups
        metrics.map((key) => (
          <option key={key} value={key}>
            {getMetricLabel(key)}
          </option>
        ))
      )}
    </select>
  );
}
