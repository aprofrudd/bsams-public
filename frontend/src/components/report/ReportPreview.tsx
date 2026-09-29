'use client';

import { forwardRef } from 'react';
import { ReportHeader } from './ReportHeader';
import { ReportJumpSection } from './ReportJumpSection';
import { ReportIsometricSection } from './ReportIsometricSection';
import { ReportMobilitySection } from './ReportMobilitySection';
import { ReportAirBikeSection } from './ReportAirBikeSection';
import type { Athlete, PerformanceEvent, ZScoreResult, MovementAssessment, AirBikeTest } from '@/lib/types';

export interface ReportData {
  athlete: Athlete;
  jumpEvents: PerformanceEvent[];
  jumpZScores: Record<string, ZScoreResult> | null;
  isometricEvents: PerformanceEvent[];
  isometricZScores: Record<string, ZScoreResult> | null;
  mobilityAssessments: MovementAssessment[];
  airBikeTests: AirBikeTest[];
}

interface ReportPreviewProps {
  data: ReportData;
  sections: Record<string, boolean>;
  notes: Record<string, string>;
  reportDate: string;
  dateRangeStart?: string | null;
  dateRangeEnd?: string | null;
}

export const ReportPreview = forwardRef<HTMLDivElement, ReportPreviewProps>(
  function ReportPreview({ data, sections, notes, reportDate, dateRangeStart, dateRangeEnd }, ref) {
    const allEnabled = Object.values(sections).every(v => v === false);
    const isEnabled = (key: string) => allEnabled || sections[key] !== false;

    return (
      <div ref={ref} className="report-print-layout">
        <ReportHeader
          athlete={data.athlete}
          reportDate={reportDate}
          dateRangeStart={dateRangeStart}
          dateRangeEnd={dateRangeEnd}
        />

        {notes.overall && (
          <div className="report-section">
            <div className="report-notes" style={{ borderLeft: '3px solid #090A3D' }}>
              <strong>Summary:</strong> {notes.overall}
            </div>
          </div>
        )}

        {isEnabled('jump') && (
          <ReportJumpSection events={data.jumpEvents} zScores={data.jumpZScores} notes={notes.jump} />
        )}

        {isEnabled('isometrics') && (
          <ReportIsometricSection events={data.isometricEvents} zScores={data.isometricZScores} notes={notes.isometrics} />
        )}

        {isEnabled('mobility') && (
          <ReportMobilitySection assessments={data.mobilityAssessments} notes={notes.mobility} />
        )}

        {isEnabled('air_bike') && (
          <ReportAirBikeSection tests={data.airBikeTests} notes={notes.air_bike} />
        )}
      </div>
    );
  }
);
