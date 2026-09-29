'use client';

import { ReportSection } from './ReportSection';
import { ReportAirBikeChart } from './ReportAirBikeChart';
import type { AirBikeTest } from '@/lib/types';
import { sprintMidPower, sprintMaxPower, midSplitLabel } from '@/lib/airBikeSplits';

interface ReportAirBikeSectionProps {
  tests: AirBikeTest[];
  notes?: string;
}

export function ReportAirBikeSection({ tests, notes }: ReportAirBikeSectionProps) {
  if (tests.length === 0) {
    return (
      <ReportSection title="Air Bike" notes={notes}>
        <p style={{ color: '#888', fontStyle: 'italic' }}>No air bike data available for this period.</p>
      </ReportSection>
    );
  }

  const formatDate = (d: string) => {
    const date = new Date(d + 'T00:00:00');
    return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  return (
    <ReportSection title="Air Bike" notes={notes}>
      {tests.map(test => {
        const sprint1 = test.sprints.find(s => s.sprint_number === 1);
        const sprint2 = test.sprints.find(s => s.sprint_number === 2);
        const s1Max = sprint1 ? sprintMaxPower(sprint1) : null;
        const s2Max = sprint2 ? sprintMaxPower(sprint2) : null;
        const dropOff = s1Max && s2Max ? (((s1Max - s2Max) / s1Max) * 100).toFixed(1) : null;

        return (
          <div key={test.id} style={{ marginBottom: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: '#090A3D', marginBottom: 8 }}>
              {formatDate(test.test_date)} — {test.body_mass_kg} kg
            </h3>
            <table style={{ marginBottom: 8 }}>
              <thead>
                <tr>
                  <th>Sprint</th>
                  <th>7s (W)</th>
                  <th>{midSplitLabel(test.split_scheme)} (W)</th>
                  <th>27s (W)</th>
                  <th>Max (W)</th>
                  <th>W/kg</th>
                  {sprint1 && <th>Lactate</th>}
                </tr>
              </thead>
              <tbody>
                {sprint1 && (
                  <tr>
                    <td>Sprint 1</td>
                    <td>{sprint1.power_7s}</td>
                    <td>{sprintMidPower(sprint1) ?? '—'}</td>
                    <td>{sprint1.power_27s}</td>
                    <td style={{ fontWeight: 600 }}>{s1Max}</td>
                    <td>{s1Max && test.body_mass_kg > 0 ? (s1Max / test.body_mass_kg).toFixed(2) : '—'}</td>
                    <td>{sprint1.blood_lactate_mmol ?? '—'}</td>
                  </tr>
                )}
                {sprint2 && (
                  <tr>
                    <td>Sprint 2</td>
                    <td>{sprint2.power_7s}</td>
                    <td>{sprintMidPower(sprint2) ?? '—'}</td>
                    <td>{sprint2.power_27s}</td>
                    <td style={{ fontWeight: 600 }}>{s2Max}</td>
                    <td>{s2Max && test.body_mass_kg > 0 ? (s2Max / test.body_mass_kg).toFixed(2) : '—'}</td>
                    <td>{sprint2.blood_lactate_mmol ?? '—'}</td>
                  </tr>
                )}
              </tbody>
            </table>
            {dropOff && (
              <p style={{ fontSize: 13, color: '#555', marginBottom: 8 }}>
                Between-sprint drop-off: <strong>{dropOff}%</strong>
              </p>
            )}
            {sprint1 && <ReportAirBikeChart test={test} />}
          </div>
        );
      })}
    </ReportSection>
  );
}
