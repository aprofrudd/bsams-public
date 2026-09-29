'use client';

import { useState } from 'react';
import type { MetabolicConfig } from '@/lib/hooks/useMetabolicProtocol';

interface MetabolicSetupProps {
  defaultWeight: number | null;
  onBegin: (config: MetabolicConfig) => void;
  bleAvailable: boolean;
}

export function MetabolicSetup({ defaultWeight, onBegin, bleAvailable }: MetabolicSetupProps) {
  const [weight, setWeight] = useState(defaultWeight ?? 75);
  const [restingLactate, setRestingLactate] = useState(1.0);
  const [dataSource, setDataSource] = useState<'ble' | 'manual'>(bleAvailable ? 'ble' : 'manual');
  const [error, setError] = useState<string | null>(null);

  function handleSubmit() {
    if (weight < 30 || weight > 250) {
      setError('Weight must be 30-250 kg');
      return;
    }
    if (restingLactate < 0 || restingLactate > 10) {
      setError('Resting lactate must be 0-10 mM');
      return;
    }
    setError(null);
    onBegin({ bodyMassKg: weight, restingLactate, dataSource });
  }

  return (
    <div className="space-y-6 max-w-sm mx-auto">
      <div className="text-center">
        <h2 className="text-xl font-heading font-bold">Anaerobic Glycolytic Profiling</h2>
        <p className="text-sm text-white/50 mt-2">
          Three sprints (10s / 20s / 30s) with rest periods and blood lactate sampling.
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="text-sm text-white/60 block mb-1">Athlete Weight (kg)</label>
          <input
            type="number"
            min={30}
            max={250}
            step={0.1}
            value={weight}
            onChange={e => setWeight(parseFloat(e.target.value) || 0)}
            className="w-full px-3 py-2 bg-primary-dark border border-secondary-muted/50 rounded-lg text-white text-center text-lg"
          />
        </div>

        <div>
          <label className="text-sm text-white/60 block mb-1">Resting Lactate (mM)</label>
          <input
            type="number"
            min={0}
            max={10}
            step={0.1}
            value={restingLactate}
            onChange={e => setRestingLactate(parseFloat(e.target.value) || 0)}
            className="w-full px-3 py-2 bg-primary-dark border border-secondary-muted/50 rounded-lg text-white text-center text-lg"
          />
        </div>

        <div>
          <label className="text-sm text-white/60 block mb-1">Data Source</label>
          <div className="flex rounded-lg overflow-hidden border border-secondary-muted/50">
            <button
              onClick={() => setDataSource('ble')}
              disabled={!bleAvailable}
              className={`flex-1 py-2.5 text-sm font-heading uppercase tracking-wider transition-colors ${
                dataSource === 'ble'
                  ? 'bg-accent text-white'
                  : 'bg-primary-dark text-white/40 hover:text-white/60'
              } disabled:opacity-30 disabled:cursor-not-allowed`}
            >
              BLE Connected
            </button>
            <button
              onClick={() => setDataSource('manual')}
              className={`flex-1 py-2.5 text-sm font-heading uppercase tracking-wider transition-colors ${
                dataSource === 'manual'
                  ? 'bg-accent text-white'
                  : 'bg-primary-dark text-white/40 hover:text-white/60'
              }`}
            >
              Manual Entry
            </button>
          </div>
          {!bleAvailable && (
            <p className="text-xs text-amber-400/70 mt-1">BLE not available in this browser</p>
          )}
        </div>
      </div>

      {error && <p className="text-sm text-red-400 text-center">{error}</p>}

      <button
        onClick={handleSubmit}
        className="btn-primary w-full py-3 text-base"
      >
        Begin Protocol
      </button>
    </div>
  );
}
