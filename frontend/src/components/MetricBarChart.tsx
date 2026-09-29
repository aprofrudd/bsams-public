'use client';

import { useState, useEffect } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { athletesApi, analysisApi } from '@/lib/api';
import { getMetricLabel } from './MetricSelector';
import type { Athlete, Benchmarks, ReferenceGroup, ZScoreResult } from '@/lib/types';

interface MetricBarChartProps {
  metric: string;
  referenceGroup: ReferenceGroup;
}

interface BarDataPoint {
  name: string;
  value: number;
  athleteId: string;
}

export function MetricBarChart({ metric, referenceGroup }: MetricBarChartProps) {
  const [data, setData] = useState<BarDataPoint[]>([]);
  const [benchmarkMean, setBenchmarkMean] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, [metric, referenceGroup]);

  async function loadData() {
    try {
      setIsLoading(true);
      setError(null);

      const [athletes, benchmarks] = await Promise.all([
        athletesApi.list(),
        analysisApi
          .getBenchmarks({ metric, referenceGroup })
          .catch(() => null),
      ]);

      setBenchmarkMean(benchmarks?.mean ?? null);

      // Get latest Z-score/value for each athlete
      const valuePromises = athletes.map((athlete) =>
        analysisApi
          .getZScore(athlete.id, { metric, referenceGroup })
          .then((result) => ({
            name: athlete.name,
            value: result.value,
            athleteId: athlete.id,
          }))
          .catch(() => null)
      );

      const results = await Promise.all(valuePromises);

      const barData = results
        .filter((r): r is BarDataPoint => r !== null)
        .sort((a, b) => b.value - a.value);

      setData(barData);
    } catch (err) {
      setError('Failed to load comparison data');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }

  const label = getMetricLabel(metric);

  if (isLoading) {
    return (
      <div className="text-center py-8">
        <div className="inline-block w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        <p className="mt-2 text-white/60">Loading comparison...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-400">{error}</p>
        <button onClick={loadData} className="btn-secondary mt-4">
          Retry
        </button>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-white/60">No comparison data available</p>
      </div>
    );
  }

  const chartHeight = Math.max(300, data.length * 40 + 60);

  return (
    <div>
      <h3 className="text-white font-medium mb-4">
        {label} - Squad Comparison
      </h3>
      <div className="max-h-[60vh] overflow-y-auto">
      <div style={{ height: chartHeight }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 10, right: 30, left: 80, bottom: 10 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#2D5585" opacity={0.5} />
            <XAxis
              type="number"
              stroke="#ffffff99"
              tick={{ fill: '#ffffff99', fontSize: 12 }}
            />
            <YAxis
              type="category"
              dataKey="name"
              stroke="#ffffff99"
              tick={{ fill: '#ffffff99', fontSize: 12 }}
              width={75}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#07083D',
                border: '1px solid #2D5585',
                borderRadius: '8px',
              }}
              labelStyle={{ color: '#ffffff99' }}
              itemStyle={{ color: '#33CBF4' }}
              formatter={(value: number) => [`${value.toFixed(2)}`, label]}
            />
            {benchmarkMean !== null && (
              <ReferenceLine
                x={benchmarkMean}
                stroke="#ffffff99"
                strokeDasharray="5 5"
                label={{
                  value: `Mean: ${benchmarkMean.toFixed(1)}`,
                  fill: '#ffffff99',
                  fontSize: 11,
                  position: 'top',
                }}
              />
            )}
            <Bar
              dataKey="value"
              fill="#33CBF4"
              radius={[0, 4, 4, 0]}
              barSize={20}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
      </div>
    </div>
  );
}
