'use client';

import { ReportSection } from './ReportSection';
import { ReportVbtChart } from './ReportVbtChart';
import type { VbtProfile } from '@/lib/types';

interface ReportVbtSectionProps {
  profiles: VbtProfile[];
  notes?: string;
}

export function ReportVbtSection({ profiles, notes }: ReportVbtSectionProps) {
  if (profiles.length === 0) {
    return (
      <ReportSection title="VBT Assessments" notes={notes}>
        <p style={{ color: '#888', fontStyle: 'italic' }}>No VBT data available for this period.</p>
      </ReportSection>
    );
  }

  const formatDate = (d: string) => {
    const date = new Date(d + 'T00:00:00');
    return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  return (
    <ReportSection title="VBT Assessments" notes={notes}>
      {profiles.map(profile => (
        <div key={profile.id} style={{ marginBottom: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: '#090A3D', marginBottom: 8 }}>
            {profile.exercise_name} — {formatDate(profile.profile_date)}
          </h3>
          {profile.analysis && (
            <div style={{ display: 'flex', gap: 20, fontSize: 13, marginBottom: 8, flexWrap: 'wrap' }}>
              <span>R² = {profile.analysis.r_squared.toFixed(4)}</span>
              {profile.analysis.estimated_1rm_kg && (
                <span>Est. 1RM = <strong>{profile.analysis.estimated_1rm_kg} kg</strong></span>
              )}
              <span>MVT = {profile.analysis.mvt_used_ms.toFixed(2)} m/s</span>
            </div>
          )}
          <table style={{ marginBottom: 8 }}>
            <thead>
              <tr>
                <th>Set</th>
                <th>Load (kg)</th>
                <th>Mean Vel (m/s)</th>
                <th>Peak Vel (m/s)</th>
              </tr>
            </thead>
            <tbody>
              {profile.sets.map(s => (
                <tr key={s.id}>
                  <td>{s.set_number}</td>
                  <td>{s.load_kg}</td>
                  <td>{s.mean_velocity_ms?.toFixed(3) ?? '—'}</td>
                  <td>{s.peak_velocity_ms?.toFixed(3) ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {profile.sets.length >= 2 && profile.analysis && (
            <ReportVbtChart profile={profile} />
          )}
        </div>
      ))}
    </ReportSection>
  );
}
