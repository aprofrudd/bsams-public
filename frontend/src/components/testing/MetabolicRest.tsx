'use client';

import { useState } from 'react';

interface MetabolicRestProps {
  restNum: 1 | 2;
  remaining: number;
  total: number;
  onSubmitLactate: (value: number) => void;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function getRestZone(restNum: 1 | 2, remaining: number, total: number): { label: string; color: string; barColor: string } {
  if (restNum === 1) {
    // Rest 1: all sit
    return { label: 'Sit still — do not move', color: 'text-red-400', barColor: 'bg-red-500' };
  }
  // Rest 2: sit 0-5min, flush 5-14min, sit 14-15min
  const elapsed = total - remaining;
  if (elapsed < 5 * 60) {
    return { label: 'Sit still — do not move', color: 'text-red-400', barColor: 'bg-red-500' };
  } else if (elapsed < 14 * 60) {
    return { label: 'Active flush — pedal gently', color: 'text-green-400', barColor: 'bg-green-500' };
  } else {
    return { label: 'Sit still — final minute', color: 'text-red-400', barColor: 'bg-red-500' };
  }
}

export function MetabolicRest({ restNum, remaining, total, onSubmitLactate }: MetabolicRestProps) {
  const [lactateValue, setLactateValue] = useState('');
  const [error, setError] = useState<string | null>(null);
  const zone = getRestZone(restNum, remaining, total);
  const showInput = remaining <= 0;

  function handleSubmit() {
    const val = parseFloat(lactateValue);
    if (isNaN(val) || val < 0 || val > 30) {
      setError('Lactate must be 0-30 mM');
      return;
    }
    setError(null);
    onSubmitLactate(val);
  }

  return (
    <div className="text-center space-y-4">
      <div className="text-lg font-heading uppercase tracking-wider text-white">
        Rest {restNum}
      </div>

      {!showInput ? (
        <>
          <div className="text-5xl font-bold font-mono text-amber-400">
            {formatTime(remaining)}
          </div>

          {/* Zone indicator bar */}
          <div className={`h-1.5 rounded-full mx-auto w-48 transition-colors ${zone.barColor}`} />

          <div className={`text-sm font-medium ${zone.color}`}>
            {zone.label}
          </div>
        </>
      ) : (
        <div className="space-y-4 max-w-xs mx-auto">
          <p className="text-sm text-white/60">
            Rest complete. Enter blood lactate measurement.
          </p>
          <div>
            <label className="text-sm text-white/60 block mb-1">
              La Peak {restNum} (mM)
            </label>
            <input
              type="number"
              min={0}
              max={30}
              step={0.1}
              value={lactateValue}
              onChange={e => setLactateValue(e.target.value)}
              autoFocus
              className="w-full px-3 py-2 bg-primary-dark border border-secondary-muted/50 rounded-lg text-white text-center text-lg"
            />
          </div>
          {error && <p className="text-xs text-red-400">{error}</p>}
          <button onClick={handleSubmit} className="btn-primary w-full py-2.5">
            Submit & Continue
          </button>
        </div>
      )}
    </div>
  );
}
