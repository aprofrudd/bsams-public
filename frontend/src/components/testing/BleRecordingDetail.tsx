'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { AirBikeRecording } from '@/lib/types';

interface BleRecordingDetailProps {
  recording: AirBikeRecording;
}

function StatCard({ label, value, unit }: { label: string; value: string | number | null; unit: string }) {
  return (
    <div className="bg-primary-dark/50 rounded p-2 text-center">
      <div className="text-[10px] text-white/30 uppercase font-heading tracking-wider">{label}</div>
      <div className="text-sm font-bold mt-0.5">
        {value != null ? value : '--'}
        <span className="text-xs text-white/30 font-normal ml-0.5">{unit}</span>
      </div>
    </div>
  );
}

export function BleRecordingDetail({ recording }: BleRecordingDetailProps) {
  const samples = recording.samples || [];
  const chartData = samples.map(s => ({
    time: (s.elapsed_ms / 1000).toFixed(1),
    watts: s.watts,
    cadence: s.cadence_rpm,
  }));

  return (
    <div className="space-y-4">
      {/* Summary stats */}
      <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
        <StatCard label="Duration" value={recording.duration_s} unit="s" />
        <StatCard label="Avg Power" value={recording.avg_power_w?.toFixed(0) ?? null} unit="W" />
        <StatCard label="Peak Power" value={recording.peak_power_w?.toFixed(0) ?? null} unit="W" />
        <StatCard
          label="Total Work"
          value={recording.total_work_j != null ? (recording.total_work_j / 1000).toFixed(1) : null}
          unit="kJ"
        />
        <StatCard label="Avg Cadence" value={recording.avg_cadence_rpm?.toFixed(0) ?? null} unit="rpm" />
        <StatCard label="Peak Cadence" value={recording.peak_cadence_rpm?.toFixed(0) ?? null} unit="rpm" />
        <StatCard label="Avg Speed" value={recording.avg_speed_kmh?.toFixed(1) ?? null} unit="km/h" />
        <StatCard label="Distance" value={recording.total_distance_m?.toFixed(0) ?? null} unit="m" />
      </div>

      {/* Power curve */}
      {chartData.length > 0 && (
        <div>
          <div className="text-xs text-white/30 uppercase font-heading tracking-wider mb-2">Power Curve</div>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2D5585" strokeOpacity={0.3} />
                <XAxis
                  dataKey="time"
                  tick={{ fill: '#2074AA', fontSize: 10 }}
                  label={{ value: 'Time (s)', fill: '#2074AA', fontSize: 10, position: 'insideBottom', offset: -5 }}
                />
                <YAxis
                  tick={{ fill: '#2074AA', fontSize: 10 }}
                  label={{ value: 'Watts', fill: '#2074AA', fontSize: 10, angle: -90, position: 'insideLeft' }}
                />
                <Tooltip
                  contentStyle={{ background: '#07083D', border: '1px solid #2D5585', borderRadius: 8, fontSize: 12 }}
                  labelStyle={{ color: '#7BA4C7' }}
                />
                <Line type="monotone" dataKey="watts" stroke="#33CBF4" strokeWidth={2} dot={false} name="Power (W)" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Cadence curve */}
      {chartData.some(d => d.cadence != null) && (
        <div>
          <div className="text-xs text-white/30 uppercase font-heading tracking-wider mb-2">Cadence Curve</div>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2D5585" strokeOpacity={0.3} />
                <XAxis
                  dataKey="time"
                  tick={{ fill: '#2074AA', fontSize: 10 }}
                  label={{ value: 'Time (s)', fill: '#2074AA', fontSize: 10, position: 'insideBottom', offset: -5 }}
                />
                <YAxis
                  tick={{ fill: '#2074AA', fontSize: 10 }}
                  label={{ value: 'RPM', fill: '#2074AA', fontSize: 10, angle: -90, position: 'insideLeft' }}
                />
                <Tooltip
                  contentStyle={{ background: '#07083D', border: '1px solid #2D5585', borderRadius: 8, fontSize: 12 }}
                  labelStyle={{ color: '#7BA4C7' }}
                />
                <Line type="monotone" dataKey="cadence" stroke="#F59E0B" strokeWidth={2} dot={false} name="Cadence (rpm)" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {recording.notes && (
        <p className="text-xs text-white/40">{recording.notes}</p>
      )}
    </div>
  );
}
