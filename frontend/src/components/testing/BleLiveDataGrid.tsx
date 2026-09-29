'use client';

import type { FtmsData } from '@/lib/bleProtocol';

interface BleLiveDataGridProps {
  data: FtmsData | null;
}

function DataCell({ label, value, unit }: { label: string; value: string; unit: string }) {
  return (
    <div className="bg-primary-dark/50 rounded-lg p-2.5">
      <div className="text-[10px] font-heading uppercase tracking-wider text-secondary-muted">
        {label}
      </div>
      <div className="text-lg font-bold font-mono mt-0.5">
        {value}
        <span className="text-xs text-secondary-muted font-normal ml-1">{unit}</span>
      </div>
    </div>
  );
}

export function BleLiveDataGrid({ data }: BleLiveDataGridProps) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
      <DataCell
        label="Speed"
        value={data?.instantSpeed != null ? data.instantSpeed.toFixed(1) : '--'}
        unit="km/h"
      />
      <DataCell
        label="Cadence"
        value={data?.instantCadence != null ? Math.round(data.instantCadence).toString() : '--'}
        unit="rpm"
      />
      <DataCell
        label="Power"
        value={data?.instantPower != null ? data.instantPower.toString() : '--'}
        unit="W"
      />
      <DataCell
        label="Distance"
        value={data?.totalDistance != null ? data.totalDistance.toString() : '--'}
        unit="m"
      />
      <DataCell
        label="Calories"
        value={data?.totalEnergy != null ? data.totalEnergy.toString() : '--'}
        unit="kcal"
      />
      <DataCell
        label="Elapsed"
        value={data?.elapsedTime != null ? data.elapsedTime.toString() : '--'}
        unit="s"
      />
    </div>
  );
}
