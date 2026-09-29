'use client';

import {
  ComposedChart,
  Scatter,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';
import type { LactateTest } from '@/lib/types';

interface ReportLactateChartProps {
  test: LactateTest;
}

export function ReportLactateChart({ test }: ReportLactateChartProps) {
  const { stages, analysis } = test;
  const unitLabel = test.test_type === 'running' ? 'km/h' : 'W';

  const lactatePoints = stages
    .filter(s => s.intensity_value != null && s.blood_lactate_mmol != null)
    .map(s => ({ intensity: s.intensity_value, lactate: s.blood_lactate_mmol }))
    .sort((a, b) => a.intensity - b.intensity);

  const hrPoints = stages
    .filter(s => s.intensity_value != null && s.heart_rate_bpm != null)
    .map(s => ({ intensity: s.intensity_value, hr: s.heart_rate_bpm! }))
    .sort((a, b) => a.intensity - b.intensity);

  if (lactatePoints.length < 2) return null;

  const segmentLines: { data: { intensity: number; lactate: number }[]; color: string }[] = [];
  if (analysis?.segments?.length === 3) {
    const colors = ['#22c55e', '#eab308', '#ef4444'];
    analysis.segments.forEach((seg, idx) => {
      const points: { intensity: number; lactate: number }[] = [];
      const range = seg.end_x - seg.start_x;
      const steps = 20;
      for (let i = 0; i <= steps; i++) {
        const x = seg.start_x + (range * i) / steps;
        points.push({ intensity: x, lactate: seg.slope * x + seg.intercept });
      }
      segmentLines.push({ data: points, color: colors[idx] });
    });
  }

  const allIntensities = lactatePoints.map(p => p.intensity);
  const xFloor = Math.floor(Math.min(...allIntensities));
  const xCeil = Math.ceil(Math.max(...allIntensities));
  const xTicks: number[] = [];
  for (let v = xFloor; v <= xCeil; v++) xTicks.push(v);

  const maxLactate = Math.max(...lactatePoints.map(p => p.lactate));

  const allHr = hrPoints.map(p => p.hr);
  const hrFloor = allHr.length > 0 ? Math.floor(Math.min(...allHr) / 10) * 10 : 0;
  const hrCeil = allHr.length > 0 ? Math.ceil(Math.max(...allHr) / 10) * 10 : 200;
  const hrTicks: number[] = [];
  for (let v = hrFloor; v <= hrCeil; v += 10) hrTicks.push(v);

  return (
    <ComposedChart width={700} height={280} margin={{ top: 25, right: 50, bottom: 20, left: 10 }}>
      <CartesianGrid strokeDasharray="3 3" stroke="#d1d5db" opacity={0.5} />
      <XAxis
        dataKey="intensity"
        type="number"
        domain={[xFloor, xCeil]}
        ticks={xTicks}
        tick={{ fill: '#333', fontSize: 11 }}
        allowDuplicatedCategory={false}
        label={{ value: `Speed (${unitLabel})`, position: 'bottom', offset: 5, fill: '#555', fontSize: 11 }}
      />
      <YAxis
        yAxisId="lactate"
        domain={[0, Math.ceil(maxLactate) + 1]}
        tick={{ fill: '#333', fontSize: 11 }}
        label={{ value: 'Lactate (mmol/L)', angle: -90, position: 'insideLeft', offset: 0, fill: '#555', fontSize: 11 }}
      />
      {hrPoints.length > 0 && (
        <YAxis
          yAxisId="hr"
          orientation="right"
          domain={[hrFloor, hrCeil]}
          ticks={hrTicks}
          tick={{ fill: '#b45309', fontSize: 11 }}
          label={{ value: 'HR (bpm)', angle: 90, position: 'insideRight', offset: 0, fill: '#b45309', fontSize: 11 }}
        />
      )}
      {test.lt1_value != null && (
        <ReferenceLine x={test.lt1_value} yAxisId="lactate" stroke="#22c55e" strokeDasharray="6 3" />
      )}
      {test.lt2_value != null && (
        <ReferenceLine x={test.lt2_value} yAxisId="lactate" stroke="#ef4444" strokeDasharray="6 3" />
      )}
      {segmentLines.map((seg, idx) => (
        <Line key={`seg-${idx}`} data={seg.data} type="linear" dataKey="lactate" stroke={seg.color} strokeWidth={2} dot={false} yAxisId="lactate" isAnimationActive={false} />
      ))}
      <Line data={lactatePoints} type="monotone" dataKey="lactate" stroke="#0891b2" strokeWidth={1.5} dot={false} yAxisId="lactate" isAnimationActive={false} />
      {hrPoints.length > 1 && (
        <Line data={hrPoints} type="monotone" dataKey="hr" stroke="#d97706" strokeWidth={1.5} dot={false} yAxisId="hr" isAnimationActive={false} />
      )}
      {hrPoints.length > 0 && (
        <Scatter data={hrPoints} dataKey="hr" fill="#d97706" stroke="#333" strokeWidth={1} yAxisId="hr" r={4} isAnimationActive={false} />
      )}
      <Scatter data={lactatePoints} dataKey="lactate" fill="#0891b2" stroke="#333" strokeWidth={1.5} yAxisId="lactate" r={5} isAnimationActive={false} />
    </ComposedChart>
  );
}
