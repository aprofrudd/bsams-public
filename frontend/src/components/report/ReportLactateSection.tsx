'use client';

import { ReportSection } from './ReportSection';
import { ReportLactateChart } from './ReportLactateChart';
import type { LactateTest } from '@/lib/types';

interface ReportLactateSectionProps {
  tests: LactateTest[];
  notes?: string;
}

export function ReportLactateSection({ tests, notes }: ReportLactateSectionProps) {
  if (tests.length === 0) {
    return (
      <ReportSection title="Lactate Profile" notes={notes}>
        <p style={{ color: '#888', fontStyle: 'italic' }}>No lactate data available for this period.</p>
      </ReportSection>
    );
  }

  const formatDate = (d: string) => {
    const date = new Date(d + 'T00:00:00');
    return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  return (
    <ReportSection title="Lactate Profile" notes={notes}>
      {tests.map(test => {
        const unitLabel = test.test_type === 'running' ? 'km/h' : 'W';
        return (
          <div key={test.id} style={{ marginBottom: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: '#090A3D', marginBottom: 8 }}>
              {test.test_type === 'running' ? 'Running' : 'Cycling'} — {formatDate(test.test_date)}
            </h3>
            <div style={{ display: 'flex', gap: 24, fontSize: 13, marginBottom: 8, flexWrap: 'wrap' }}>
              {test.lt1_value != null && (
                <span>LT1: <strong>{test.lt1_value} {unitLabel}</strong>
                  {test.lt1_lactate != null && <span style={{ color: '#888' }}> ({test.lt1_lactate} mmol/L)</span>}
                  {test.lt1_hr != null && <span style={{ color: '#888' }}> @ {test.lt1_hr} bpm</span>}
                </span>
              )}
              {test.lt2_value != null && (
                <span>LT2: <strong>{test.lt2_value} {unitLabel}</strong>
                  {test.lt2_lactate != null && <span style={{ color: '#888' }}> ({test.lt2_lactate} mmol/L)</span>}
                  {test.lt2_hr != null && <span style={{ color: '#888' }}> @ {test.lt2_hr} bpm</span>}
                </span>
              )}
            </div>
            {test.stages.length >= 2 && (
              <ReportLactateChart test={test} />
            )}
          </div>
        );
      })}
    </ReportSection>
  );
}
