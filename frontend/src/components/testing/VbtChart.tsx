'use client';

import {
  ComposedChart,
  Scatter,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import type { VbtProfile } from '@/lib/types';

interface VbtChartProps {
  profile: VbtProfile;
}

interface DataPoint {
  load_kg: number;
  velocity_ms: number;
}

export function VbtChart({ profile }: VbtChartProps) {
  const { sets, analysis } = profile;

  // Build scatter data from sets (prefer mean velocity, fall back to peak)
  const scatterData: DataPoint[] = sets
    .filter((s) => s.mean_velocity_ms != null || s.peak_velocity_ms != null)
    .map((s) => ({
      load_kg: s.load_kg,
      velocity_ms: (s.mean_velocity_ms ?? s.peak_velocity_ms)!,
    }))
    .sort((a, b) => a.load_kg - b.load_kg);

  if (scatterData.length < 2 || !analysis) {
    return (
      <p className="text-sm text-white/40 text-center py-4">
        Need at least 2 sets with velocity data for chart
      </p>
    );
  }

  // Build regression line from min load to 1RM (or max load + 20%)
  const minLoad = Math.min(...scatterData.map((d) => d.load_kg));
  const maxLoad = analysis.estimated_1rm_kg
    ? Math.max(analysis.estimated_1rm_kg, ...scatterData.map((d) => d.load_kg))
    : Math.max(...scatterData.map((d) => d.load_kg)) * 1.2;

  const lineSteps = 50;
  const lineData = Array.from({ length: lineSteps + 1 }, (_, i) => {
    const load = minLoad + ((maxLoad - minLoad) * i) / lineSteps;
    const vel = analysis.slope * load + analysis.intercept;
    return { load_kg: load, regression_velocity: Math.max(vel, 0) };
  });

  // Combine scatter + line data for the chart
  const combinedData = lineData.map((ld) => {
    const match = scatterData.find(
      (sd) => Math.abs(sd.load_kg - ld.load_kg) < 0.5
    );
    return {
      ...ld,
      velocity_ms: match?.velocity_ms ?? undefined,
    };
  });

  // Ensure all scatter points are included
  for (const sp of scatterData) {
    const exists = combinedData.find(
      (d) => d.velocity_ms === sp.velocity_ms && Math.abs(d.load_kg - sp.load_kg) < 0.5
    );
    if (!exists) {
      combinedData.push({
        load_kg: sp.load_kg,
        regression_velocity: analysis.slope * sp.load_kg + analysis.intercept,
        velocity_ms: sp.velocity_ms,
      });
    }
  }

  combinedData.sort((a, b) => a.load_kg - b.load_kg);

  const maxVelocity = Math.max(...scatterData.map((d) => d.velocity_ms));

  return (
    <div>
      <div className="h-[220px] sm:h-[280px] md:h-[320px]">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart
          data={combinedData}
          margin={{ top: 10, right: 20, bottom: 20, left: 10 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#2D5585" opacity={0.3} />
          <XAxis
            dataKey="load_kg"
            type="number"
            domain={[minLoad * 0.9, maxLoad * 1.05]}
            tick={{ fill: '#ffffff80', fontSize: 11 }}
            label={{
              value: 'Load (kg)',
              position: 'bottom',
              offset: 5,
              fill: '#ffffff60',
              fontSize: 11,
            }}
          />
          <YAxis
            domain={[0, Math.ceil(maxVelocity * 10) / 10 + 0.1]}
            tick={{ fill: '#ffffff80', fontSize: 11 }}
            label={{
              value: 'Velocity (m/s)',
              angle: -90,
              position: 'insideLeft',
              offset: 0,
              fill: '#ffffff60',
              fontSize: 11,
            }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#07083D',
              border: '1px solid #2D5585',
              borderRadius: 8,
              fontSize: 12,
            }}
            labelFormatter={(val) => `${Number(val).toFixed(1)} kg`}
            formatter={(value: number, name: string) => {
              if (name === 'velocity_ms') return [value.toFixed(3) + ' m/s', 'Velocity'];
              if (name === 'regression_velocity') return [value.toFixed(3) + ' m/s', 'Regression'];
              return [value, name];
            }}
          />

          {/* MVT horizontal line */}
          <ReferenceLine
            y={analysis.mvt_used_ms}
            stroke="#ef4444"
            strokeDasharray="6 3"
            label={{
              value: `MVT ${analysis.mvt_used_ms.toFixed(2)}`,
              position: 'right',
              fill: '#ef4444',
              fontSize: 10,
            }}
          />

          {/* 1RM vertical line */}
          {analysis.estimated_1rm_kg && (
            <ReferenceLine
              x={analysis.estimated_1rm_kg}
              stroke="#22c55e"
              strokeDasharray="6 3"
              label={{
                value: `1RM ${analysis.estimated_1rm_kg} kg`,
                position: 'top',
                fill: '#22c55e',
                fontSize: 10,
              }}
            />
          )}

          {/* Regression line */}
          <Line
            type="linear"
            dataKey="regression_velocity"
            stroke="#f59e0b"
            strokeDasharray="6 3"
            strokeWidth={2}
            dot={false}
            activeDot={false}
          />

          {/* Scatter points */}
          <Scatter
            dataKey="velocity_ms"
            fill="#33CBF4"
            stroke="#ffffff"
            strokeWidth={1.5}
            r={5}
          />
        </ComposedChart>
      </ResponsiveContainer>
      </div>

      {/* R² display */}
      <div className="text-center text-xs text-white/40 mt-1">
        R² = {analysis.r_squared.toFixed(4)}
        {analysis.estimated_1rm_kg && (
          <span className="ml-3">
            Est. 1RM = <span className="text-white/80 font-semibold">{analysis.estimated_1rm_kg} kg</span>
          </span>
        )}
      </div>
    </div>
  );
}
