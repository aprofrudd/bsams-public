'use client';

import { ReportSection } from './ReportSection';
import type { MovementAssessment } from '@/lib/types';

interface ReportMobilitySectionProps {
  assessments: MovementAssessment[];
  notes?: string;
}

const ASSESSMENT_LABELS: Record<string, string> = {
  overhead_squat: 'Overhead Squat',
  single_leg_squat_left: 'Single Leg Squat (Left)',
  single_leg_squat_right: 'Single Leg Squat (Right)',
};

export function ReportMobilitySection({ assessments, notes }: ReportMobilitySectionProps) {
  if (assessments.length === 0) {
    return (
      <ReportSection title="Mobility Assessments" notes={notes}>
        <p style={{ color: '#888', fontStyle: 'italic' }}>No mobility assessment data available for this period.</p>
      </ReportSection>
    );
  }

  const formatDate = (d: string) => {
    const date = new Date(d + 'T00:00:00');
    return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  return (
    <ReportSection title="Mobility Assessments" notes={notes}>
      {assessments.map(assessment => (
        <div key={assessment.id} style={{ marginBottom: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: '#090A3D', marginBottom: 4 }}>
            {ASSESSMENT_LABELS[assessment.assessment_type] || assessment.assessment_type} — {formatDate(assessment.assessment_date)}
          </h3>
          {assessment.summary && (
            <p style={{ fontSize: 13, color: '#555', marginBottom: 8 }}>{assessment.summary}</p>
          )}
          {assessment.photos && assessment.photos.length > 0 && (
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
              {assessment.photos.map(photo => (
                photo.photo_url && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    key={photo.id}
                    src={photo.photo_url}
                    alt={photo.view_type}
                    style={{ width: 150, height: 150, objectFit: 'cover', borderRadius: 4, border: '1px solid #d1d5db' }}
                    crossOrigin="anonymous"
                  />
                )
              ))}
            </div>
          )}
          {assessment.notes && (
            <p style={{ fontSize: 12, color: '#888', fontStyle: 'italic' }}>{assessment.notes}</p>
          )}
        </div>
      ))}
    </ReportSection>
  );
}
