'use client';

import { MetricSelector } from './MetricSelector';
import type { ReferenceGroup, ViewMode, BenchmarkSource } from '@/lib/types';

interface DataViewControlsProps {
  referenceGroup: ReferenceGroup;
  onReferenceGroupChange: (group: ReferenceGroup) => void;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  selectedMetric: string;
  onMetricChange: (metric: string) => void;
  athleteId?: string;
  disabled?: boolean;
  benchmarkSource?: BenchmarkSource;
  onBenchmarkSourceChange?: (source: BenchmarkSource) => void;
  role?: 'coach' | 'admin' | 'athlete';
  dataVersion?: number;
  metricFilter?: string[];
  onMetricsAvailable?: (count: number) => void;
}

export function DataViewControls({
  referenceGroup,
  onReferenceGroupChange,
  viewMode,
  onViewModeChange,
  selectedMetric,
  onMetricChange,
  athleteId,
  disabled = false,
  benchmarkSource,
  onBenchmarkSourceChange,
  role,
  dataVersion,
  metricFilter,
  onMetricsAvailable,
}: DataViewControlsProps) {
  return (
    <div className="card">
      <div className="flex flex-wrap items-end gap-3 sm:gap-4">
        {/* Variable Selector */}
        <div className="w-full sm:w-auto sm:flex-1 sm:min-w-[180px]">
          <label className="block text-sm text-white/60 mb-1">Variable</label>
          {athleteId ? (
            <MetricSelector
              athleteId={athleteId}
              selectedMetric={selectedMetric}
              onMetricChange={onMetricChange}
              disabled={disabled}
              dataVersion={dataVersion}
              metricFilter={metricFilter}
              onMetricsAvailable={onMetricsAvailable}
            />
          ) : (
            <select className="select w-full" disabled>
              <option>Select an athlete first</option>
            </select>
          )}
        </div>

        {/* Reference Group Selector */}
        <div className="w-full sm:w-auto sm:flex-1 sm:min-w-[180px]">
          <label className="block text-sm text-white/60 mb-1">Reference Group</label>
          <select
            value={referenceGroup}
            onChange={(e) => onReferenceGroupChange(e.target.value as ReferenceGroup)}
            disabled={disabled}
            className="select w-full"
          >
            <option value="cohort">Whole Cohort</option>
            <option value="gender">Gender Specific</option>
            <option value="mass_band">Mass Band (5kg)</option>
          </select>
        </div>

        {/* Benchmark Source Toggle (admin only) */}
        {role === 'admin' && benchmarkSource && onBenchmarkSourceChange && (
          <div className="w-full sm:w-auto">
            <label className="block text-sm text-white/60 mb-1">Benchmark Source</label>
            <div className="flex rounded-lg overflow-hidden border border-secondary-muted">
              <button
                onClick={() => onBenchmarkSourceChange('boxing_science')}
                disabled={disabled}
                className={`px-3 py-2.5 min-h-[44px] text-sm font-medium transition-colors ${
                  benchmarkSource === 'boxing_science'
                    ? 'bg-accent text-primary'
                    : 'bg-primary-dark text-white hover:bg-secondary-muted active:bg-secondary-muted/80'
                }`}
              >
                Boxing Science
              </button>
              <button
                onClick={() => onBenchmarkSourceChange('shared_pool')}
                disabled={disabled}
                className={`px-3 py-2.5 min-h-[44px] text-sm font-medium transition-colors ${
                  benchmarkSource === 'shared_pool'
                    ? 'bg-accent text-primary'
                    : 'bg-primary-dark text-white hover:bg-secondary-muted active:bg-secondary-muted/80'
                }`}
              >
                Shared Pool
              </button>
              <button
                onClick={() => onBenchmarkSourceChange('own')}
                disabled={disabled}
                className={`px-3 py-2.5 min-h-[44px] text-sm font-medium transition-colors ${
                  benchmarkSource === 'own'
                    ? 'bg-accent text-primary'
                    : 'bg-primary-dark text-white hover:bg-secondary-muted active:bg-secondary-muted/80'
                }`}
              >
                My Data
              </button>
            </div>
          </div>
        )}

        {/* View Mode Toggle */}
        <div className="flex-shrink-0">
          <label className="block text-sm text-white/60 mb-1">View</label>
          <div className="flex rounded-lg overflow-hidden border border-secondary-muted">
            <button
              onClick={() => onViewModeChange('table')}
              disabled={disabled}
              className={`px-3 sm:px-4 py-2.5 min-h-[44px] text-sm font-medium transition-colors ${
                viewMode === 'table'
                  ? 'bg-accent text-primary'
                  : 'bg-primary-dark text-white hover:bg-secondary-muted active:bg-secondary-muted/80'
              }`}
            >
              <TableIcon />
            </button>
            <button
              onClick={() => onViewModeChange('graph')}
              disabled={disabled}
              className={`px-3 sm:px-4 py-2.5 min-h-[44px] text-sm font-medium transition-colors ${
                viewMode === 'graph'
                  ? 'bg-accent text-primary'
                  : 'bg-primary-dark text-white hover:bg-secondary-muted active:bg-secondary-muted/80'
              }`}
            >
              <GraphIcon />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function TableIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
      <line x1="3" y1="9" x2="21" y2="9" />
      <line x1="3" y1="15" x2="21" y2="15" />
      <line x1="9" y1="3" x2="9" y2="21" />
    </svg>
  );
}

function GraphIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </svg>
  );
}
