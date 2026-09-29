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
  Legend,
} from 'recharts';
import type { AirBikeTest } from '@/lib/types';
import { sprintMidPower, sprintMaxPower, sprintMidSeconds, splitTicks } from '@/lib/airBikeSplits';

interface AirBikeChartProps {
  test: AirBikeTest;
}

export function AirBikeChart({ test }: AirBikeChartProps) {
  const { sprints, body_mass_kg } = test;
  const sprint1 = sprints.find((s) => s.sprint_number === 1);
  const sprint2 = sprints.find((s) => s.sprint_number === 2);

  if (!sprint1) {
    return (
      <p className="text-sm text-white/40 text-center py-4">
        No sprint data available for chart
      </p>
    );
  }

  // The mid split is 14s or 17s depending on the protocol used for this test
  const midSeconds = sprintMidSeconds(sprint1, test.split_scheme);

  // Build merged data for Recharts
  const chartData = [
    {
      time: 7,
      sprint1: sprint1.power_7s,
      ...(sprint2 ? { sprint2: sprint2.power_7s } : {}),
    },
    {
      time: midSeconds,
      sprint1: sprintMidPower(sprint1),
      ...(sprint2 ? { sprint2: sprintMidPower(sprint2) } : {}),
    },
    {
      time: 27,
      sprint1: sprint1.power_27s,
      ...(sprint2 ? { sprint2: sprint2.power_27s } : {}),
    },
  ];

  // Compute max powers
  const s1Max = sprintMaxPower(sprint1);
  const s2Max = sprint2 ? sprintMaxPower(sprint2) : null;

  // Y-axis auto-scale
  // sprint1 can be null at the mid split if the value was never recorded
  const allPowers = chartData.flatMap((d) => {
    const vals: number[] = [];
    if (d.sprint1 != null) vals.push(d.sprint1 as number);
    if ('sprint2' in d && d.sprint2 != null) vals.push(d.sprint2 as number);
    return vals;
  });
  const minPower = Math.min(...allPowers);
  const maxPower = Math.max(...allPowers);
  const yFloor = Math.floor(minPower / 50) * 50;
  const yCeil = Math.ceil(maxPower / 50) * 50 + 50;

  // Drop-off percentage
  const dropOff = s2Max != null ? (((s1Max - s2Max) / s1Max) * 100).toFixed(1) : null;

  return (
    <div>
      <div className="h-[220px] sm:h-[280px] md:h-[320px]">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={chartData} margin={{ top: 15, right: 20, bottom: 20, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2D5585" opacity={0.3} />
          <XAxis
            dataKey="time"
            type="number"
            domain={[0, 30]}
            ticks={splitTicks(test.split_scheme)}
            tickFormatter={(val) => `${val}s`}
            tick={{ fill: '#ffffff80', fontSize: 11 }}
            label={{
              value: 'Time (s)',
              position: 'bottom',
              offset: 5,
              fill: '#ffffff60',
              fontSize: 11,
            }}
          />
          <YAxis
            domain={[yFloor, yCeil]}
            tick={{ fill: '#ffffff80', fontSize: 11 }}
            label={{
              value: 'Power (W)',
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
            labelFormatter={(val) => `${val}s`}
            formatter={(value: number, name: string) => {
              const label = name === 'sprint1' ? 'Sprint 1' : 'Sprint 2';
              return [`${value} W`, label];
            }}
          />
          <Legend
            verticalAlign="top"
            align="right"
            formatter={(value) => (value === 'sprint1' ? 'Sprint 1' : 'Sprint 2')}
            wrapperStyle={{ fontSize: 11, color: '#ffffff80', paddingBottom: 4 }}
          />

          {/* Sprint 1 Line + Scatter */}
          <Line
            type="monotone"
            dataKey="sprint1"
            stroke="#33CBF4"
            strokeWidth={2}
            dot={false}
            activeDot={false}
            isAnimationActive={false}
          />
          <Scatter
            dataKey="sprint1"
            fill="#33CBF4"
            stroke="#ffffff"
            strokeWidth={1.5}
            r={5}
            isAnimationActive={false}
          />

          {/* Sprint 2 Line + Scatter (if exists) */}
          {sprint2 && (
            <>
              <Line
                type="monotone"
                dataKey="sprint2"
                stroke="#f59e0b"
                strokeWidth={2}
                dot={false}
                activeDot={false}
                isAnimationActive={false}
              />
              <Scatter
                dataKey="sprint2"
                fill="#f59e0b"
                stroke="#ffffff"
                strokeWidth={1.5}
                r={5}
                isAnimationActive={false}
              />
            </>
          )}

          {/* Future: benchmark ReferenceLine placeholder */}
        </ComposedChart>
      </ResponsiveContainer>
      </div>

      {/* Summary below chart */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-white/60 mt-2 justify-center">
        <span>
          Sprint 1 max: <span className="text-accent font-semibold">{s1Max} W</span>
          {body_mass_kg > 0 && (
            <span className="text-white/40"> ({(s1Max / body_mass_kg).toFixed(2)} W/kg)</span>
          )}
        </span>
        {s2Max != null && (
          <>
            <span className="text-white/20">|</span>
            <span>
              Sprint 2 max: <span className="text-amber-400 font-semibold">{s2Max} W</span>
              {body_mass_kg > 0 && (
                <span className="text-white/40"> ({(s2Max / body_mass_kg).toFixed(2)} W/kg)</span>
              )}
            </span>
            <span className="text-white/20">|</span>
            <span>
              Drop-off: <span className="text-white font-semibold">{dropOff}%</span>
            </span>
          </>
        )}
      </div>
    </div>
  );
}
