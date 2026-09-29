'use client';

import { ReportSection } from './ReportSection';
import { METRIC_DEFINITIONS } from '@/lib/metricRegistry';
import type { PerformanceEvent, ZScoreResult } from '@/lib/types';

const ISOMETRIC_METRICS = METRIC_DEFINITIONS.filter(m => m.group === 'isometric');

interface ReportIsometricSectionProps {
  events: PerformanceEvent[];
  zScores: Record<string, ZScoreResult> | null;
  notes?: string;
}

export function ReportIsometricSection({ events, zScores, notes }: ReportIsometricSectionProps) {
  if (events.length === 0) {
    return (
      <ReportSection title="Isometrics" notes={notes}>
        <p style={{ color: '#888', fontStyle: 'italic' }}>No isometric data available for this period.</p>
      </ReportSection>
    );
  }

  const latestByMetric: Record<string, { value: number; date: string }> = {};
  const sortedEvents = [...events].sort((a, b) => b.event_date.localeCompare(a.event_date));

  for (const event of sortedEvents) {
    for (const metric of ISOMETRIC_METRICS) {
      if (latestByMetric[metric.key]) continue;
      const val = event.metrics[metric.key];
      if (val != null && typeof val === 'number') {
        latestByMetric[metric.key] = { value: val, date: event.event_date };
      }
    }
  }

  const metricsWithData = ISOMETRIC_METRICS.filter(m => latestByMetric[m.key]);

  if (metricsWithData.length === 0) {
    return (
      <ReportSection title="Isometrics" notes={notes}>
        <p style={{ color: '#888', fontStyle: 'italic' }}>No isometric metrics found in events.</p>
      </ReportSection>
    );
  }

  const formatDate = (d: string) => {
    const date = new Date(d + 'T00:00:00');
    return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  const getZColor = (z: number) => {
    if (z >= 1) return '#22c55e';
    if (z >= 0) return '#06b6d4';
    if (z >= -1) return '#eab308';
    return '#ef4444';
  };

  return (
    <ReportSection title="Isometrics" notes={notes}>
      <table>
        <thead>
          <tr>
            <th>Metric</th>
            <th>Value</th>
            <th>Date</th>
            {zScores && <th>Z-Score</th>}
          </tr>
        </thead>
        <tbody>
          {metricsWithData.map(metric => {
            const data = latestByMetric[metric.key];
            const zs = zScores?.[metric.key];
            return (
              <tr key={metric.key}>
                <td>{metric.label}</td>
                <td style={{ fontWeight: 600 }}>{data.value.toFixed(1)} {metric.unit}</td>
                <td style={{ color: '#888' }}>{formatDate(data.date)}</td>
                {zScores && (
                  <td style={{ fontWeight: 600, color: zs ? getZColor(zs.z_score) : '#888' }}>
                    {zs ? zs.z_score.toFixed(2) : 'N/A'}
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </ReportSection>
  );
}
