'use client';

import {
  ComposedChart,
  Scatter,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend,
} from 'recharts';
import type { AirBikeTest } from '@/lib/types';
import { sprintMidPower, sprintMidSeconds, splitTicks } from '@/lib/airBikeSplits';

interface ReportAirBikeChartProps {
  test: AirBikeTest;
}

export function ReportAirBikeChart({ test }: ReportAirBikeChartProps) {
  const sprint1 = test.sprints.find(s => s.sprint_number === 1);
  const sprint2 = test.sprints.find(s => s.sprint_number === 2);

  if (!sprint1) return null;

  const midSeconds = sprintMidSeconds(sprint1, test.split_scheme);

  const chartData = [
    { time: 7, sprint1: sprint1.power_7s, ...(sprint2 ? { sprint2: sprint2.power_7s } : {}) },
    { time: midSeconds, sprint1: sprintMidPower(sprint1), ...(sprint2 ? { sprint2: sprintMidPower(sprint2) } : {}) },
    { time: 27, sprint1: sprint1.power_27s, ...(sprint2 ? { sprint2: sprint2.power_27s } : {}) },
  ];

  const allPowers = chartData.flatMap(d => {
    const vals: number[] = [];
    if (d.sprint1 != null) vals.push(d.sprint1 as number);
    if ('sprint2' in d && d.sprint2 != null) vals.push(d.sprint2 as number);
    return vals;
  });
  const yFloor = Math.floor(Math.min(...allPowers) / 50) * 50;
  const yCeil = Math.ceil(Math.max(...allPowers) / 50) * 50 + 50;

  return (
    <ComposedChart width={700} height={250} data={chartData} margin={{ top: 15, right: 20, bottom: 20, left: 10 }}>
      <CartesianGrid strokeDasharray="3 3" stroke="#d1d5db" opacity={0.5} />
      <XAxis
        dataKey="time"
        type="number"
        domain={[0, 30]}
        ticks={splitTicks(test.split_scheme)}
        tickFormatter={val => `${val}s`}
        tick={{ fill: '#333', fontSize: 11 }}
        label={{ value: 'Time (s)', position: 'bottom', offset: 5, fill: '#555', fontSize: 11 }}
      />
      <YAxis
        domain={[yFloor, yCeil]}
        tick={{ fill: '#333', fontSize: 11 }}
        label={{ value: 'Power (W)', angle: -90, position: 'insideLeft', offset: 0, fill: '#555', fontSize: 11 }}
      />
      <Legend
        verticalAlign="top"
        align="right"
        formatter={value => (value === 'sprint1' ? 'Sprint 1' : 'Sprint 2')}
        wrapperStyle={{ fontSize: 11, color: '#333', paddingBottom: 4 }}
      />
      <Line type="monotone" dataKey="sprint1" stroke="#0891b2" strokeWidth={2} dot={false} isAnimationActive={false} />
      <Scatter dataKey="sprint1" fill="#0891b2" stroke="#333" strokeWidth={1.5} r={5} isAnimationActive={false} />
      {sprint2 && (
        <>
          <Line type="monotone" dataKey="sprint2" stroke="#d97706" strokeWidth={2} dot={false} isAnimationActive={false} />
          <Scatter dataKey="sprint2" fill="#d97706" stroke="#333" strokeWidth={1.5} r={5} isAnimationActive={false} />
        </>
      )}
    </ComposedChart>
  );
}
