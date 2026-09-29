'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { useAthleteContext } from '@/lib/contexts/AthleteContext';
import {
  eventsApi,
  assessmentApi,
  airBikeApi,
  analysisApi,
  reportsApi,
} from '@/lib/api';
import NoAthleteSelected from '@/components/NoAthleteSelected';
import { ReportPreview } from '@/components/report/ReportPreview';
import type { ReportData } from '@/components/report/ReportPreview';
import { METRIC_DEFINITIONS } from '@/lib/metricRegistry';
import type {
  PerformanceEvent,
  MovementAssessment,
  AirBikeTest,
  TestReportListItem,
  ZScoreResult,
} from '@/lib/types';

const JUMP_KEYS = METRIC_DEFINITIONS.filter(m => m.group === 'jump').map(m => m.key);
const ISOMETRIC_KEYS = METRIC_DEFINITIONS.filter(m => m.group === 'isometric').map(m => m.key);

const SECTION_DEFS = [
  { key: 'jump', label: 'Jump Assessments' },
  { key: 'isometrics', label: 'Isometrics' },
  { key: 'mobility', label: 'Mobility Assessments' },
  { key: 'air_bike', label: 'Air Bike' },
];

const DEFAULT_SECTIONS: Record<string, boolean> = Object.fromEntries(SECTION_DEFS.map(s => [s.key, true]));

function todayStr() {
  return new Date().toISOString().split('T')[0];
}

export default function TestReportPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const { selectedAthlete } = useAthleteContext();
  const reportRef = useRef<HTMLDivElement>(null);

  // Config state
  const [reportDate, setReportDate] = useState(todayStr());
  const [dateRangeStart, setDateRangeStart] = useState('');
  const [dateRangeEnd, setDateRangeEnd] = useState('');
  const [sections, setSections] = useState<Record<string, boolean>>({ ...DEFAULT_SECTIONS });
  const [notes, setNotes] = useState<Record<string, string>>({});

  // UI state
  const [mode, setMode] = useState<'config' | 'preview'>('config');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');

  // Report data
  const [reportData, setReportData] = useState<ReportData | null>(null);
  const [dataWarnings, setDataWarnings] = useState<string[]>([]);

  // Saved reports
  const [savedReports, setSavedReports] = useState<TestReportListItem[]>([]);
  const [activeReportId, setActiveReportId] = useState<string | null>(null);
  const [isLoadingReports, setIsLoadingReports] = useState(false);

  // Auth guard: redirect athletes
  useEffect(() => {
    if (!loading && user?.role === 'athlete') {
      router.replace('/training');
    }
  }, [loading, user, router]);

  useEffect(() => {
    if (!loading && !user) {
      router.replace('/login');
    }
  }, [loading, user, router]);

  // Load saved reports when athlete changes
  useEffect(() => {
    if (selectedAthlete && user) {
      loadSavedReports();
    }
    setMode('config');
    setReportData(null);
    setActiveReportId(null);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedAthlete?.id]);

  const loadSavedReports = useCallback(async () => {
    if (!selectedAthlete) return;
    setIsLoadingReports(true);
    try {
      const reports = await reportsApi.listForAthlete(selectedAthlete.id);
      setSavedReports(reports);
    } catch {
      // silently handle
    } finally {
      setIsLoadingReports(false);
    }
  }, [selectedAthlete]);

  // Split events into jump vs isometric
  function splitEvents(events: PerformanceEvent[]) {
    const jumpEvents: PerformanceEvent[] = [];
    const isometricEvents: PerformanceEvent[] = [];
    for (const e of events) {
      const hasJump = JUMP_KEYS.some(k => e.metrics[k] != null);
      const hasIso = ISOMETRIC_KEYS.some(k => e.metrics[k] != null);
      if (hasJump) jumpEvents.push(e);
      if (hasIso) isometricEvents.push(e);
    }
    return { jumpEvents, isometricEvents };
  }

  // Fetch Z-scores for latest event's metrics
  async function fetchZScores(athleteId: string, metricKeys: string[]): Promise<Record<string, ZScoreResult> | null> {
    try {
      const results: Record<string, ZScoreResult> = {};
      const promises = metricKeys.map(async (key) => {
        try {
          const zs = await analysisApi.getZScore(athleteId, {
            metric: key,
            referenceGroup: 'cohort',
          });
          results[key] = zs;
        } catch {
          // skip metrics without enough data
        }
      });
      await Promise.all(promises);
      return Object.keys(results).length > 0 ? results : null;
    } catch {
      return null;
    }
  }

  async function handleGenerate() {
    if (!selectedAthlete) return;
    setIsGenerating(true);
    setError('');

    try {
      const athleteId = selectedAthlete.id;
      const dateOpts = dateRangeStart && dateRangeEnd
        ? { startDate: dateRangeStart, endDate: dateRangeEnd }
        : undefined;

      // Parallel fetch all data sources
      const [eventsResult, assessmentsResult, airBikeResult] =
        await Promise.allSettled([
          eventsApi.listForAthlete(athleteId, dateOpts),
          assessmentApi.listAssessments(athleteId),
          airBikeApi.listTests(athleteId),
        ]);

      // Collect warnings for failed data sources
      const sourceNames: [PromiseSettledResult<any>, string][] = [
        [eventsResult, 'Performance Events'],
        [assessmentsResult, 'Movement Assessments'],
        [airBikeResult, 'Air Bike Tests'],
      ];
      const warnings = sourceNames
        .filter(([result]) => result.status === 'rejected')
        .map(([, name]) => name);
      setDataWarnings(warnings);

      const events = eventsResult.status === 'fulfilled' ? eventsResult.value : [];
      const assessmentList = assessmentsResult.status === 'fulfilled' ? assessmentsResult.value : [];
      const airBikeList = airBikeResult.status === 'fulfilled' ? airBikeResult.value : [];

      // Split events
      const { jumpEvents, isometricEvents } = splitEvents(events);

      // Date-filter AirBike/Assessments client-side if date range set
      const filterByDate = <T,>(items: T[], dateField: string): T[] => {
        if (!dateRangeStart || !dateRangeEnd) return items;
        return items.filter(item => {
          const d = (item as any)[dateField] as string | undefined;
          return d != null && d >= dateRangeStart && d <= dateRangeEnd;
        });
      };

      const filteredAssessments = filterByDate(assessmentList, 'assessment_date');
      const filteredAirBike = filterByDate(airBikeList, 'test_date');

      // Fetch full detail for the most recent items (for charts)
      const mobilityAssessments: MovementAssessment[] = [];
      if (sections.mobility !== false && filteredAssessments.length > 0) {
        // Get most recent of each assessment type
        const byType = new Map<string, string>();
        for (const a of filteredAssessments) {
          if (!byType.has(a.assessment_type)) {
            byType.set(a.assessment_type, a.id);
          }
        }
        const assessPromises = Array.from(byType.values()).map(id =>
          assessmentApi.getAssessment(id).catch(() => null)
        );
        const assessResults = await Promise.all(assessPromises);
        for (const a of assessResults) {
          if (a) mobilityAssessments.push(a);
        }
      }

      const airBikeTests: AirBikeTest[] = [];
      if (sections.air_bike !== false && filteredAirBike.length > 0) {
        const mostRecent = filteredAirBike[0];
        try {
          const full = await airBikeApi.getTest(mostRecent.id);
          airBikeTests.push(full);
        } catch { /* skip */ }
      }

      // Fetch Z-scores for jump and isometric metrics
      const jumpZScores = sections.jump !== false && jumpEvents.length > 0
        ? await fetchZScores(athleteId, JUMP_KEYS)
        : null;
      const isometricZScores = sections.isometrics !== false && isometricEvents.length > 0
        ? await fetchZScores(athleteId, ISOMETRIC_KEYS)
        : null;

      setReportData({
        athlete: selectedAthlete,
        jumpEvents,
        jumpZScores,
        isometricEvents,
        isometricZScores,
        mobilityAssessments,
        airBikeTests,
      });
      setMode('preview');
    } catch (err: any) {
      setError(err.message || 'Failed to generate report');
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleExportPdf() {
    if (!reportRef.current || !selectedAthlete) return;
    setIsExporting(true);

    try {
      const jsPDF = (await import('jspdf')).default;
      const html2canvas = (await import('html2canvas')).default;

      const container = reportRef.current;
      const reportSections = container.querySelectorAll('.report-section');

      const pdf = new jsPDF('p', 'mm', 'a4');
      const contentWidth = 190; // 210mm - 2x10mm margin

      for (let i = 0; i < reportSections.length; i++) {
        const canvas = await html2canvas(reportSections[i] as HTMLElement, {
          scale: 2,
          useCORS: true,
          backgroundColor: '#ffffff',
        });
        const imgData = canvas.toDataURL('image/jpeg', 0.95);
        const imgHeight = (canvas.height * contentWidth) / canvas.width;

        if (i > 0) pdf.addPage();
        pdf.addImage(imgData, 'JPEG', 10, 10, contentWidth, imgHeight);
      }

      const date = todayStr();
      const safeName = selectedAthlete.name.replace(/[^a-zA-Z0-9]/g, '_');
      pdf.save(`${safeName}_Test_Report_${date}.pdf`);
    } catch (err: any) {
      setError(err.message || 'Failed to export PDF');
    } finally {
      setIsExporting(false);
    }
  }

  async function handleSaveReport() {
    if (!selectedAthlete) return;
    setIsSaving(true);
    setError('');

    try {
      const reportPayload = {
        athlete_id: selectedAthlete.id,
        report_date: reportDate,
        date_range_start: dateRangeStart || undefined,
        date_range_end: dateRangeEnd || undefined,
        sections,
        notes,
      };

      if (activeReportId) {
        await reportsApi.update(activeReportId, {
          report_date: reportDate,
          date_range_start: dateRangeStart || undefined,
          date_range_end: dateRangeEnd || undefined,
          sections,
          notes,
        });
      } else {
        const created = await reportsApi.create(reportPayload);
        setActiveReportId(created.id);
      }

      await loadSavedReports();
    } catch (err: any) {
      setError(err.message || 'Failed to save report');
    } finally {
      setIsSaving(false);
    }
  }

  async function handleLoadReport(reportId: string) {
    try {
      const report = await reportsApi.get(reportId);
      setReportDate(report.report_date);
      setDateRangeStart(report.date_range_start || '');
      setDateRangeEnd(report.date_range_end || '');
      setSections(report.sections);
      setNotes(report.notes);
      setActiveReportId(report.id);
      setMode('config');
      setReportData(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load report');
    }
  }

  async function handleDeleteReport(reportId: string) {
    try {
      await reportsApi.delete(reportId);
      if (activeReportId === reportId) {
        setActiveReportId(null);
      }
      await loadSavedReports();
    } catch (err: any) {
      setError(err.message || 'Failed to delete report');
    }
  }

  const formatDate = (d: string) => {
    const date = new Date(d + 'T00:00:00');
    return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  const enabledCount = Object.values(sections).filter(v => v).length;

  if (loading || !user) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (user.role === 'athlete') return null;

  return (
    <div className="space-y-4 md:space-y-6">
      <h2 className="section-title text-base sm:text-lg">Reports</h2>

      {!selectedAthlete ? (
        <NoAthleteSelected message="Select an athlete to create a report" />
      ) : mode === 'config' ? (
        /* Config Mode */
        <div className="space-y-4">
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-red-400 text-sm">
              {error}
            </div>
          )}

          {/* Report Settings */}
          <div className="card space-y-4">
            <h3 className="font-heading text-sm uppercase tracking-wider text-white/60">Report Settings</h3>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs text-white/40 mb-1">Report Date</label>
                <input
                  type="date"
                  value={reportDate}
                  onChange={e => setReportDate(e.target.value)}
                  className="input w-full text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-white/40 mb-1">Date Range Start</label>
                <input
                  type="date"
                  value={dateRangeStart}
                  onChange={e => setDateRangeStart(e.target.value)}
                  className="input w-full text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-white/40 mb-1">Date Range End</label>
                <input
                  type="date"
                  value={dateRangeEnd}
                  onChange={e => setDateRangeEnd(e.target.value)}
                  className="input w-full text-sm"
                />
              </div>
            </div>
          </div>

          {/* Sections */}
          <div className="card space-y-3">
            <h3 className="font-heading text-sm uppercase tracking-wider text-white/60">Sections</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {SECTION_DEFS.map(s => (
                <label key={s.key} className="flex items-center gap-2 cursor-pointer min-h-[44px] px-3 py-2 rounded-lg hover:bg-white/5 transition-colors">
                  <input
                    type="checkbox"
                    checked={sections[s.key] !== false}
                    onChange={e => setSections(prev => ({ ...prev, [s.key]: e.target.checked }))}
                    className="w-4 h-4 rounded accent-[#33CBF4]"
                  />
                  <span className="text-sm text-white/80">{s.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Notes */}
          <div className="card space-y-3">
            <h3 className="font-heading text-sm uppercase tracking-wider text-white/60">Coach Notes</h3>
            <div>
              <label className="block text-xs text-white/40 mb-1">Overall Summary</label>
              <textarea
                value={notes.overall || ''}
                onChange={e => setNotes(prev => ({ ...prev, overall: e.target.value }))}
                placeholder="Overall athlete summary and feedback..."
                className="input w-full text-sm resize-y min-h-[60px] sm:min-h-[80px]"
                rows={3}
              />
            </div>
            {SECTION_DEFS.filter(s => sections[s.key] !== false).map(s => (
              <div key={s.key}>
                <label className="block text-xs text-white/40 mb-1">{s.label} Notes</label>
                <textarea
                  value={notes[s.key] || ''}
                  onChange={e => setNotes(prev => ({ ...prev, [s.key]: e.target.value }))}
                  placeholder={`Notes for ${s.label}...`}
                  className="input w-full text-sm resize-y"
                  rows={2}
                />
              </div>
            ))}
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap gap-3">
            <button
              onClick={handleGenerate}
              disabled={isGenerating || enabledCount === 0}
              className="btn-primary flex items-center gap-2"
            >
              {isGenerating ? (
                <>
                  <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                  Generating...
                </>
              ) : (
                'Generate Preview'
              )}
            </button>
            <button
              onClick={handleSaveReport}
              disabled={isSaving}
              className="btn-secondary flex items-center gap-2"
            >
              {isSaving ? 'Saving...' : activeReportId ? 'Update Report' : 'Save Report'}
            </button>
          </div>

          {enabledCount === 0 && (
            <p className="text-yellow-400 text-sm">Select at least one section to generate a report.</p>
          )}

          {/* Saved Reports List */}
          <div className="card space-y-3">
            <h3 className="font-heading text-sm uppercase tracking-wider text-white/60">Saved Reports</h3>
            {isLoadingReports ? (
              <div className="text-center py-4">
                <div className="inline-block w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
              </div>
            ) : savedReports.length === 0 ? (
              <p className="text-white/30 text-sm py-4 text-center">No saved reports for this athlete</p>
            ) : (
              <div className="space-y-2">
                {savedReports.map(report => (
                  <div
                    key={report.id}
                    className={`flex items-center justify-between px-4 py-3 min-h-[44px] rounded-lg border transition-colors ${
                      activeReportId === report.id
                        ? 'border-accent bg-accent/10'
                        : 'border-secondary-muted hover:border-accent/30'
                    }`}
                  >
                    <div>
                      <span className="text-sm text-white/80">{formatDate(report.report_date)}</span>
                      <span className="text-xs text-white/30 ml-2">
                        Created {formatDate(report.created_at.split('T')[0])}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleLoadReport(report.id)}
                        className="text-xs text-accent hover:text-accent/80 px-3 py-1.5 min-h-[44px] rounded transition-colors"
                      >
                        Load
                      </button>
                      <button
                        onClick={() => handleDeleteReport(report.id)}
                        className="text-xs text-red-400 hover:text-red-300 px-3 py-1.5 min-h-[44px] rounded transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Preview Mode */
        <div className="space-y-4">
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-red-400 text-sm">
              {error}
            </div>
          )}

          {dataWarnings.length > 0 && (
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg px-4 py-3 text-yellow-400 text-sm">
              Warning: Some data sources failed to load: {dataWarnings.join(', ')}
            </div>
          )}

          {/* Action Bar */}
          <div className="flex flex-wrap gap-3 no-print">
            <button onClick={() => { setMode('config'); setDataWarnings([]); }} className="btn-secondary">
              Back to Settings
            </button>
            <button
              onClick={handleExportPdf}
              disabled={isExporting}
              className="btn-primary flex items-center gap-2"
            >
              {isExporting ? (
                <>
                  <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                  Exporting...
                </>
              ) : (
                'Export PDF'
              )}
            </button>
            <button
              onClick={handleSaveReport}
              disabled={isSaving}
              className="btn-secondary flex items-center gap-2"
            >
              {isSaving ? 'Saving...' : activeReportId ? 'Update Report' : 'Save Report'}
            </button>
          </div>

          {/* Report Preview */}
          {reportData && (
            <div className="rounded-xl overflow-hidden shadow-lg">
              <ReportPreview
                ref={reportRef}
                data={reportData}
                sections={sections}
                notes={notes}
                reportDate={reportDate}
                dateRangeStart={dateRangeStart || null}
                dateRangeEnd={dateRangeEnd || null}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
