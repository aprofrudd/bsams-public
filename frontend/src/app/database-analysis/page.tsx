'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { databaseAnalysisApi } from '@/lib/api';
import { Spinner } from '@/components/Spinner';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ErrorBar,
} from 'recharts';
import type {
  AggregationMode,
  AnalysisDomain,
  AnalysisDataSource,
  AnalysisRequest,
  AnalysisResponse,
  DescriptiveStats,
  DysfunctionPrevalence,
  DomainMetric,
} from '@/lib/types';

const DOMAINS: { key: AnalysisDomain; label: string }[] = [
  { key: 'performance', label: 'Performance' },
  { key: 'training', label: 'Training' },
  { key: 'wellness', label: 'Wellness' },
  { key: 'vbt', label: 'VBT' },
  { key: 'lactate', label: 'Lactate' },
  { key: 'air_bike', label: 'Air Bike' },
  { key: 'assessments', label: 'Assessments' },
];

const MASS_BANDS = [
  '45-49.9kg', '50-54.9kg', '55-59.9kg', '60-64.9kg', '65-69.9kg',
  '70-74.9kg', '75-79.9kg', '80-84.9kg', '85-89.9kg', '90-94.9kg',
  '95-99.9kg', '100-104.9kg', '105-109.9kg', '110-114.9kg',
];

const AGGREGATION_MODES: { key: AggregationMode; label: string }[] = [
  { key: 'all_records', label: 'All Records' },
  { key: 'mean_per_athlete', label: 'Mean/Athlete' },
  { key: 'median_per_athlete', label: 'Median/Athlete' },
  { key: 'peak_per_athlete', label: 'Peak/Athlete' },
];

export default function DatabaseAnalysisPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  // Domain & source
  const [domain, setDomain] = useState<AnalysisDomain>('performance');
  const [dataSource, setDataSource] = useState<AnalysisDataSource>('boxing_science');
  const [aggregationMode, setAggregationMode] = useState<AggregationMode>('all_records');

  // Filters
  const [gender, setGender] = useState<string>('');
  const [status, setStatus] = useState<string>('');
  const [ageMin, setAgeMin] = useState<string>('');
  const [ageMax, setAgeMax] = useState<string>('');
  const [massBand, setMassBand] = useState<string>('');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [filtersOpen, setFiltersOpen] = useState(true);

  // Domain-specific filters
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([]);
  const [trainingType, setTrainingType] = useState<string>('');
  const [exerciseName, setExerciseName] = useState<string>('');
  const [testType, setTestType] = useState<string>('');
  const [assessmentType, setAssessmentType] = useState<string>('');

  // Domain metrics for filter dropdowns
  const [domainMetrics, setDomainMetrics] = useState<DomainMetric[]>([]);

  // Results
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Auth guard
  useEffect(() => {
    if (!authLoading && !user) router.replace('/login');
    if (!authLoading && user && user.role !== 'admin') router.replace('/training');
  }, [authLoading, user, router]);

  // Load domain metrics when domain changes
  useEffect(() => {
    let cancelled = false;
    async function loadMetrics() {
      try {
        const resp = await databaseAnalysisApi.getDomainMetrics(domain);
        if (!cancelled) setDomainMetrics(resp.metrics);
      } catch {
        if (!cancelled) setDomainMetrics([]);
      }
    }
    loadMetrics();
    // Reset domain-specific filters
    setSelectedMetrics([]);
    setTrainingType('');
    setExerciseName('');
    setTestType('');
    setAssessmentType('');
    return () => { cancelled = true; };
  }, [domain]);

  const runAnalysis = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const request: AnalysisRequest = {
        domain,
        data_source: dataSource,
        aggregation_mode: aggregationMode,
      };

      // Athlete filters
      const athleteFilter: AnalysisRequest['athlete_filter'] = {};
      if (gender) athleteFilter.gender = gender as 'male' | 'female';
      if (status) athleteFilter.status = status as 'amateur' | 'professional';
      if (ageMin) athleteFilter.age_min = parseInt(ageMin);
      if (ageMax) athleteFilter.age_max = parseInt(ageMax);
      if (massBand) athleteFilter.mass_band = massBand;
      if (Object.keys(athleteFilter).length > 0) request.athlete_filter = athleteFilter;

      // Date filter
      const dateFilter: AnalysisRequest['date_filter'] = {};
      if (startDate) dateFilter.start_date = startDate;
      if (endDate) dateFilter.end_date = endDate;
      if (Object.keys(dateFilter).length > 0) request.date_filter = dateFilter;

      // Domain-specific filters
      if (domain === 'performance' && selectedMetrics.length > 0) {
        request.performance_filters = { metric_keys: selectedMetrics };
      }
      if (domain === 'training' && trainingType) {
        request.training_filters = { training_type: trainingType };
      }
      if (domain === 'vbt' && exerciseName) {
        request.vbt_filters = { exercise_name: exerciseName };
      }
      if (domain === 'lactate' && testType) {
        request.lactate_filters = { test_type: testType };
      }
      if (domain === 'assessments' && assessmentType) {
        request.assessment_filters = { assessment_type: assessmentType };
      }

      const data = await databaseAnalysisApi.analyze(request);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, [domain, dataSource, aggregationMode, gender, status, ageMin, ageMax, massBand, startDate, endDate, selectedMetrics, trainingType, exerciseName, testType, assessmentType]);

  if (authLoading || !user || user.role !== 'admin') {
    return (
      <div className="page-container">
        <Spinner message="Loading..." />
      </div>
    );
  }

  return (
    <div className="page-container">
      <h1 className="section-title">Database Analysis</h1>

      {/* Domain tabs */}
      <div className="flex flex-wrap gap-1 mb-6">
        {DOMAINS.map((d) => (
          <button
            key={d.key}
            onClick={() => setDomain(d.key)}
            className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
              domain === d.key
                ? 'bg-[#33CBF4] text-[#07083D]'
                : 'bg-[#0D1B3E] text-[#ffffff99] hover:text-white hover:bg-[#1a2d5a]'
            }`}
          >
            {d.label}
          </button>
        ))}
      </div>

      {/* Filter panel */}
      <div className="card mb-6">
        <button
          onClick={() => setFiltersOpen(!filtersOpen)}
          className="w-full flex items-center justify-between text-left"
        >
          <h2 className="text-lg font-semibold text-white">Filters</h2>
          <span className="text-[#ffffff66]">{filtersOpen ? '▲' : '▼'}</span>
        </button>

        {filtersOpen && (
          <div className="mt-4 space-y-4">
            {/* Data source */}
            <div>
              <label className="block text-sm text-[#ffffff99] mb-1">Data Source</label>
              <div className="flex gap-2">
                {(['boxing_science', 'shared_pool'] as const).map((src) => (
                  <button
                    key={src}
                    onClick={() => setDataSource(src)}
                    className={`px-3 py-1.5 rounded text-sm ${
                      dataSource === src
                        ? 'bg-[#33CBF4] text-[#07083D]'
                        : 'bg-[#0D1B3E] text-[#ffffff99] hover:text-white'
                    }`}
                  >
                    {src === 'boxing_science' ? 'Boxing Science' : 'Shared Pool'}
                  </button>
                ))}
              </div>
            </div>

            {/* Aggregation mode — hidden for assessments */}
            {domain !== 'assessments' && (
              <div>
                <label className="block text-sm text-[#ffffff99] mb-1">Aggregation Mode</label>
                <div className="flex flex-wrap gap-2">
                  {AGGREGATION_MODES.map((m) => (
                    <button
                      key={m.key}
                      onClick={() => setAggregationMode(m.key)}
                      className={`px-3 py-1.5 rounded text-sm ${
                        aggregationMode === m.key
                          ? 'bg-[#33CBF4] text-[#07083D]'
                          : 'bg-[#0D1B3E] text-[#ffffff99] hover:text-white'
                      }`}
                    >
                      {m.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Gender + Status */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-[#ffffff99] mb-1">Gender</label>
                <div className="flex gap-2">
                  {['', 'male', 'female'].map((g) => (
                    <button
                      key={g}
                      onClick={() => setGender(g)}
                      className={`px-3 py-1.5 rounded text-sm ${
                        gender === g
                          ? 'bg-[#33CBF4] text-[#07083D]'
                          : 'bg-[#0D1B3E] text-[#ffffff99] hover:text-white'
                      }`}
                    >
                      {g || 'All'}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm text-[#ffffff99] mb-1">Status</label>
                <div className="flex gap-2">
                  {['', 'amateur', 'professional'].map((s) => (
                    <button
                      key={s}
                      onClick={() => setStatus(s)}
                      className={`px-3 py-1.5 rounded text-sm ${
                        status === s
                          ? 'bg-[#33CBF4] text-[#07083D]'
                          : 'bg-[#0D1B3E] text-[#ffffff99] hover:text-white'
                      }`}
                    >
                      {s || 'All'}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Age range + Date range */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-[#ffffff99] mb-1">Age Range</label>
                <div className="flex gap-2 items-center">
                  <input
                    type="number"
                    placeholder="Min"
                    value={ageMin}
                    onChange={(e) => setAgeMin(e.target.value)}
                    className="w-20 px-2 py-1.5 rounded bg-[#0D1B3E] border border-[#2D5585] text-white text-sm"
                  />
                  <span className="text-[#ffffff66]">-</span>
                  <input
                    type="number"
                    placeholder="Max"
                    value={ageMax}
                    onChange={(e) => setAgeMax(e.target.value)}
                    className="w-20 px-2 py-1.5 rounded bg-[#0D1B3E] border border-[#2D5585] text-white text-sm"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm text-[#ffffff99] mb-1">Mass Band</label>
                <select
                  value={massBand}
                  onChange={(e) => setMassBand(e.target.value)}
                  className="w-full px-2 py-1.5 rounded bg-[#0D1B3E] border border-[#2D5585] text-white text-sm"
                >
                  <option value="">All</option>
                  {MASS_BANDS.map((mb) => (
                    <option key={mb} value={mb}>{mb}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Date range */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-[#ffffff99] mb-1">Start Date</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full px-2 py-1.5 rounded bg-[#0D1B3E] border border-[#2D5585] text-white text-sm"
                />
              </div>
              <div>
                <label className="block text-sm text-[#ffffff99] mb-1">End Date</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full px-2 py-1.5 rounded bg-[#0D1B3E] border border-[#2D5585] text-white text-sm"
                />
              </div>
            </div>

            {/* Domain-specific filters */}
            {domain === 'performance' && domainMetrics.length > 0 && (
              <div>
                <label className="block text-sm text-[#ffffff99] mb-1">Metrics (leave empty for all)</label>
                <div className="flex flex-wrap gap-2">
                  {domainMetrics.map((m) => (
                    <button
                      key={m.key}
                      onClick={() => {
                        setSelectedMetrics((prev) =>
                          prev.includes(m.key)
                            ? prev.filter((k) => k !== m.key)
                            : [...prev, m.key]
                        );
                      }}
                      className={`px-2 py-1 rounded text-xs ${
                        selectedMetrics.includes(m.key)
                          ? 'bg-[#33CBF4] text-[#07083D]'
                          : 'bg-[#0D1B3E] text-[#ffffff99] hover:text-white'
                      }`}
                    >
                      {m.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {domain === 'training' && (
              <div>
                <label className="block text-sm text-[#ffffff99] mb-1">Training Type</label>
                <input
                  type="text"
                  placeholder="e.g. boxing, s&c"
                  value={trainingType}
                  onChange={(e) => setTrainingType(e.target.value)}
                  className="w-full max-w-xs px-2 py-1.5 rounded bg-[#0D1B3E] border border-[#2D5585] text-white text-sm"
                />
              </div>
            )}

            {domain === 'vbt' && (
              <div>
                <label className="block text-sm text-[#ffffff99] mb-1">Exercise Name</label>
                <input
                  type="text"
                  placeholder="e.g. Back Squat"
                  value={exerciseName}
                  onChange={(e) => setExerciseName(e.target.value)}
                  className="w-full max-w-xs px-2 py-1.5 rounded bg-[#0D1B3E] border border-[#2D5585] text-white text-sm"
                />
              </div>
            )}

            {domain === 'lactate' && (
              <div>
                <label className="block text-sm text-[#ffffff99] mb-1">Test Type</label>
                <input
                  type="text"
                  placeholder="e.g. running, cycling"
                  value={testType}
                  onChange={(e) => setTestType(e.target.value)}
                  className="w-full max-w-xs px-2 py-1.5 rounded bg-[#0D1B3E] border border-[#2D5585] text-white text-sm"
                />
              </div>
            )}

            {domain === 'assessments' && (
              <div>
                <label className="block text-sm text-[#ffffff99] mb-1">Assessment Type</label>
                <select
                  value={assessmentType}
                  onChange={(e) => setAssessmentType(e.target.value)}
                  className="w-full max-w-xs px-2 py-1.5 rounded bg-[#0D1B3E] border border-[#2D5585] text-white text-sm"
                >
                  <option value="">All</option>
                  <option value="overhead_squat">Overhead Squat</option>
                  <option value="single_leg_squat_left">Single Leg Squat (Left)</option>
                  <option value="single_leg_squat_right">Single Leg Squat (Right)</option>
                </select>
              </div>
            )}

            {/* Run button */}
            <button
              onClick={runAnalysis}
              disabled={loading}
              className="btn-primary"
            >
              {loading ? 'Analysing...' : 'Run Analysis'}
            </button>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="card mb-6 border border-red-500/50">
          <p className="text-red-400">{error}</p>
        </div>
      )}

      {/* Results */}
      {result && (
        <>
          {/* Summary */}
          <div className="card mb-6">
            <p className="text-[#ffffff99]">
              <span className="text-white font-semibold">{result.athlete_count}</span> athletes,{' '}
              <span className="text-white font-semibold">{result.record_count}</span> records matched
              {result.aggregation_mode && result.aggregation_mode !== 'all_records' && (
                <span className="ml-2 text-[#33CBF4]">
                  ({result.aggregation_mode.replace(/_/g, ' ')})
                </span>
              )}
            </p>
          </div>

          {/* Statistics table */}
          {result.statistics.length > 0 && (
            <div className="card mb-6 overflow-x-auto">
              <h2 className="text-lg font-semibold text-white mb-3">Descriptive Statistics</h2>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[#2D5585]">
                    <th className="text-left py-2 px-3 text-[#ffffff99]">Metric</th>
                    <th className="text-right py-2 px-3 text-[#ffffff99]">N</th>
                    <th className="text-right py-2 px-3 text-[#ffffff99]">Mean</th>
                    <th className="text-right py-2 px-3 text-[#ffffff99]">SD</th>
                    <th className="text-right py-2 px-3 text-[#ffffff99]">SWC</th>
                    <th className="text-right py-2 px-3 text-[#ffffff99]">Median</th>
                    <th className="text-right py-2 px-3 text-[#ffffff99]">Min</th>
                    <th className="text-right py-2 px-3 text-[#ffffff99]">Max</th>
                    <th className="text-right py-2 px-3 text-[#ffffff99]">95% CI</th>
                  </tr>
                </thead>
                <tbody>
                  {result.statistics.map((s) => (
                    <tr key={s.metric} className="border-b border-[#2D5585]/50 hover:bg-[#0D1B3E]/50">
                      <td className="py-2 px-3 text-white">{s.label}</td>
                      <td className="py-2 px-3 text-right text-[#ffffff99]">{s.count}</td>
                      <td className="py-2 px-3 text-right text-white">{s.mean?.toFixed(2) ?? '-'}</td>
                      <td className="py-2 px-3 text-right text-[#ffffff99]">{s.std_dev?.toFixed(2) ?? '-'}</td>
                      <td className="py-2 px-3 text-right text-[#f59e0b]">{s.std_dev != null ? (0.2 * s.std_dev).toFixed(2) : '-'}</td>
                      <td className="py-2 px-3 text-right text-[#ffffff99]">{s.median?.toFixed(2) ?? '-'}</td>
                      <td className="py-2 px-3 text-right text-[#ffffff99]">{s.min_val?.toFixed(2) ?? '-'}</td>
                      <td className="py-2 px-3 text-right text-[#ffffff99]">{s.max_val?.toFixed(2) ?? '-'}</td>
                      <td className="py-2 px-3 text-right text-[#ffffff99]">
                        {s.ci_lower != null && s.ci_upper != null
                          ? `${s.ci_lower.toFixed(2)} - ${s.ci_upper.toFixed(2)}`
                          : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Bar chart — means with SD error bars */}
          {result.statistics.length > 0 && (
            <div className="card mb-6">
              <h2 className="text-lg font-semibold text-white mb-3">Mean Values</h2>
              <div style={{ height: Math.max(250, result.statistics.length * 45) }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={result.statistics
                      .filter((s) => s.mean != null)
                      .map((s) => ({
                        name: s.label,
                        mean: s.mean,
                        errorMargin: s.std_dev ?? 0,
                      }))}
                    layout="vertical"
                    margin={{ top: 10, right: 30, left: 120, bottom: 10 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#2D5585" opacity={0.5} />
                    <XAxis type="number" stroke="#ffffff99" />
                    <YAxis type="category" dataKey="name" stroke="#ffffff99" width={110} tick={{ fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#07083D', border: '1px solid #2D5585', borderRadius: '8px' }}
                      labelStyle={{ color: '#ffffff99' }}
                      formatter={(value: number) => [value.toFixed(2), 'Mean']}
                    />
                    <Bar dataKey="mean" fill="#33CBF4" radius={[0, 4, 4, 0]} barSize={20}>
                      <ErrorBar dataKey="errorMargin" stroke="#ffffff66" strokeWidth={1.5} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Assessment: dysfunction prevalence chart */}
          {result.dysfunction_prevalence.length > 0 && (
            <div className="card mb-6">
              <h2 className="text-lg font-semibold text-white mb-3">Dysfunction Prevalence</h2>
              <div className="overflow-x-auto mb-4">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[#2D5585]">
                      <th className="text-left py-2 px-3 text-[#ffffff99]">Region</th>
                      <th className="text-left py-2 px-3 text-[#ffffff99]">Dysfunction</th>
                      <th className="text-right py-2 px-3 text-[#ffffff99]">Count</th>
                      <th className="text-right py-2 px-3 text-[#ffffff99]">Total</th>
                      <th className="text-right py-2 px-3 text-[#ffffff99]">Prevalence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.dysfunction_prevalence.map((d, i) => (
                      <tr key={i} className="border-b border-[#2D5585]/50 hover:bg-[#0D1B3E]/50">
                        <td className="py-2 px-3 text-white capitalize">{d.region.replace(/_/g, ' ')}</td>
                        <td className="py-2 px-3 text-white capitalize">{d.dysfunction.replace(/_/g, ' ')}</td>
                        <td className="py-2 px-3 text-right text-[#ffffff99]">{d.count}</td>
                        <td className="py-2 px-3 text-right text-[#ffffff99]">{d.total_assessed}</td>
                        <td className="py-2 px-3 text-right text-white">{d.prevalence_pct.toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div style={{ height: Math.max(250, result.dysfunction_prevalence.length * 40) }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={result.dysfunction_prevalence.map((d) => ({
                      name: `${d.region.replace(/_/g, ' ')} - ${d.dysfunction.replace(/_/g, ' ')}`,
                      prevalence: d.prevalence_pct,
                    }))}
                    layout="vertical"
                    margin={{ top: 10, right: 30, left: 160, bottom: 10 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#2D5585" opacity={0.5} />
                    <XAxis type="number" domain={[0, 100]} stroke="#ffffff99" unit="%" />
                    <YAxis type="category" dataKey="name" stroke="#ffffff99" width={150} tick={{ fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#07083D', border: '1px solid #2D5585', borderRadius: '8px' }}
                      formatter={(value: number) => [`${value.toFixed(1)}%`, 'Prevalence']}
                    />
                    <Bar dataKey="prevalence" fill="#F59E0B" radius={[0, 4, 4, 0]} barSize={18} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
