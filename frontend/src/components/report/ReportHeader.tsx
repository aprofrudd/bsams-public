'use client';

import type { Athlete } from '@/lib/types';

interface ReportHeaderProps {
  athlete: Athlete;
  reportDate: string;
  dateRangeStart?: string | null;
  dateRangeEnd?: string | null;
}

export function ReportHeader({ athlete, reportDate, dateRangeStart, dateRangeEnd }: ReportHeaderProps) {
  const formatDate = (d: string) => {
    const date = new Date(d + 'T00:00:00');
    return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  return (
    <div className="report-section" style={{ borderBottom: '2px solid #090A3D', paddingBottom: 16, marginBottom: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/boxing-science-logo.png"
            alt="Boxing Science"
            style={{ height: 50, marginBottom: 8 }}
            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
          />
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#090A3D', margin: 0, fontFamily: 'var(--font-chakra), Chakra Petch, sans-serif', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Athlete Test Report
          </h1>
        </div>
        <div style={{ textAlign: 'right', fontSize: 13, color: '#555' }}>
          <div style={{ fontSize: 15, fontWeight: 600, color: '#090A3D' }}>{athlete.name}</div>
          {athlete.gender && <div style={{ textTransform: 'capitalize' }}>{athlete.gender}</div>}
          {athlete.body_mass_kg && <div>{athlete.body_mass_kg} kg</div>}
          {athlete.stature_cm && <div>{athlete.stature_cm} cm</div>}
          <div style={{ marginTop: 6, color: '#888' }}>
            Report: {formatDate(reportDate)}
          </div>
          {dateRangeStart && dateRangeEnd && (
            <div style={{ color: '#888' }}>
              Period: {formatDate(dateRangeStart)} &ndash; {formatDate(dateRangeEnd)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
