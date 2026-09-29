'use client';

import { useState, useEffect, useCallback } from 'react';
import { trainingApi } from '@/lib/api';
import type { TrainingLoadAnalysis } from '@/lib/types';

interface LoadChartProps {
  athleteId: string;
  dataVersion?: number;
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
}

function getAcwrColor(acwr: number | null): string {
  if (acwr === null) return 'text-white/60';
  if (acwr >= 0.8 && acwr <= 1.3) return 'text-green-400';
  if (acwr > 1.5) return 'text-red-400';
  return 'text-yellow-400';
}

function getAcwrLabel(acwr: number | null): string {
  if (acwr === null) return 'Insufficient data';
  if (acwr >= 0.8 && acwr <= 1.3) return 'Optimal';
  if (acwr > 1.5) return 'High Risk';
  if (acwr < 0.8) return 'Undertraining';
  return 'Caution';
}

export function LoadChart({ athleteId, dataVersion }: LoadChartProps) {
  const [analysis, setAnalysis] = useState<TrainingLoadAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await trainingApi.getLoadAnalysis(athleteId, 28);
      setAnalysis(data);
    } catch (err) {
      setError('Failed to load training analysis');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [athleteId]);

  useEffect(() => {
    loadData();
  }, [loadData, dataVersion]);

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return <p className="text-red-400 text-sm py-4 text-center">{error}</p>;
  }

  if (!analysis) return null;

  const maxLoad = Math.max(...analysis.daily_loads.map((d) => d.total_srpe), 1);

  return (
    <div>
      <h3 className="section-title text-base mb-4">Training Load</h3>

      {/* Key Metrics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div className="bg-secondary-muted/20 rounded-lg p-3 text-center">
          <div className="text-xs text-white/60 mb-1">Weekly Load</div>
          <div className="text-lg font-bold text-white">
            {analysis.weekly_load ?? '-'}
          </div>
        </div>
        <div className="bg-secondary-muted/20 rounded-lg p-3 text-center">
          <div className="text-xs text-white/60 mb-1">Monotony</div>
          <div className="text-lg font-bold text-white">
            {analysis.monotony ?? '-'}
          </div>
        </div>
        <div className="bg-secondary-muted/20 rounded-lg p-3 text-center">
          <div className="text-xs text-white/60 mb-1">Strain</div>
          <div className="text-lg font-bold text-white">
            {analysis.strain ?? '-'}
          </div>
        </div>
        <div className="bg-secondary-muted/20 rounded-lg p-3 text-center">
          <div className="text-xs text-white/60 mb-1">ACWR</div>
          <div className={`text-lg font-bold ${getAcwrColor(analysis.acwr)}`}>
            {analysis.acwr ?? '-'}
          </div>
          <div className={`text-xs ${getAcwrColor(analysis.acwr)}`}>
            {getAcwrLabel(analysis.acwr)}
          </div>
        </div>
      </div>

      {/* ACWR Guidance */}
      {analysis.acwr !== null && analysis.acwr > 1.5 && (
        <p className="text-red-400 text-xs mb-3">Consider reducing session intensity or adding a rest day</p>
      )}
      {analysis.acwr !== null && analysis.acwr < 0.8 && (
        <p className="text-yellow-400 text-xs mb-3">Consider increasing training volume gradually</p>
      )}
      {analysis.acwr !== null && analysis.acwr > 1.3 && analysis.acwr <= 1.5 && (
        <p className="text-yellow-400 text-xs mb-3">Monitor load — approaching high-risk zone</p>
      )}

      {/* Daily Load Bar Chart */}
      <div className="overflow-x-auto">
        <div className="flex">
          {/* Y-axis labels */}
          <div className="flex flex-col justify-between h-32 pr-2 shrink-0">
            <span className="text-[10px] text-white/40 leading-none">{maxLoad}</span>
            <span className="text-[10px] text-white/40 leading-none">{Math.round(maxLoad / 2)}</span>
            <span className="text-[10px] text-white/40 leading-none">0</span>
          </div>
          {/* Bars */}
          <div className="flex-1 min-w-0">
            <div className="relative h-32">
              {/* Grid lines */}
              <div className="absolute inset-0 flex flex-col justify-between pointer-events-none">
                <div className="border-t border-white/10" />
                <div className="border-t border-white/10" />
                <div className="border-t border-white/10" />
              </div>
              <div className="flex items-end gap-0.5 min-w-fit h-full relative">
                {analysis.daily_loads.map((dl) => {
                  const height = maxLoad > 0 ? (dl.total_srpe / maxLoad) * 100 : 0;
                  return (
                    <div
                      key={dl.date}
                      className="flex flex-col justify-end items-center h-full"
                      style={{ minWidth: '20px' }}
                    >
                      <div
                        className="w-6 sm:w-4 rounded-t-sm bg-accent/70 hover:bg-accent transition-colors"
                        style={{ height: `${height}%`, minHeight: dl.total_srpe > 0 ? '2px' : '0' }}
                        title={`${formatDate(dl.date)}: ${dl.total_srpe} sRPE (${dl.session_count} session${dl.session_count !== 1 ? 's' : ''})`}
                      />
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="flex gap-0.5 mt-1">
              {analysis.daily_loads.map((dl, i) => (
                <div
                  key={dl.date}
                  className="text-center"
                  style={{ minWidth: '20px' }}
                >
                  {i % 7 === 0 && (
                    <span className="text-[9px] text-white/40">{formatDate(dl.date)}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="text-[10px] text-white/40 text-center mt-1">sRPE (Daily Load)</div>
      </div>

      {/* Acute/Chronic Info */}
      {(analysis.acute_load !== null || analysis.chronic_load !== null) && (
        <div className="flex gap-4 mt-3 text-xs text-white/60">
          {analysis.acute_load !== null && (
            <span>Acute (7d avg): <span className="text-white font-medium">{analysis.acute_load}</span></span>
          )}
          {analysis.chronic_load !== null && (
            <span>Chronic (28d avg): <span className="text-white font-medium">{analysis.chronic_load}</span></span>
          )}
        </div>
      )}
    </div>
  );
}
