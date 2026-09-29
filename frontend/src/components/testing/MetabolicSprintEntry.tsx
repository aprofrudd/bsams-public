'use client';

import { useState } from 'react';

interface MetabolicSprintEntryProps {
  onSubmit: (powers: [number, number, number], lactates: [number, number, number]) => void;
}

export function MetabolicSprintEntry({ onSubmit }: MetabolicSprintEntryProps) {
  const [power1, setPower1] = useState('');
  const [power2, setPower2] = useState('');
  const [power3, setPower3] = useState('');
  const [la1, setLa1] = useState('');
  const [la2, setLa2] = useState('');
  const [la3, setLa3] = useState('');
  const [error, setError] = useState<string | null>(null);

  function handleSubmit() {
    const powers = [parseFloat(power1), parseFloat(power2), parseFloat(power3)];
    const lactates = [parseFloat(la1), parseFloat(la2), parseFloat(la3)];

    for (let i = 0; i < 3; i++) {
      if (isNaN(powers[i]) || powers[i] < 0 || powers[i] > 3000) {
        setError(`Sprint ${i + 1} power must be 0-3000 W`);
        return;
      }
      if (isNaN(lactates[i]) || lactates[i] < 0 || lactates[i] > 30) {
        setError(`La Peak ${i + 1} must be 0-30 mM`);
        return;
      }
    }

    setError(null);
    onSubmit(
      powers as [number, number, number],
      lactates as [number, number, number]
    );
  }

  return (
    <div className="space-y-4 max-w-sm mx-auto">
      <div className="text-center">
        <h3 className="text-lg font-heading uppercase tracking-wider">Manual Data Entry</h3>
        <p className="text-xs text-white/40 mt-1">
          Enter average power (W) for each 10s analysis segment and peak lactate values.
        </p>
      </div>

      {[
        { label: 'Sprint 1 avg power (W) — 0-10s', value: power1, set: setPower1, laLabel: 'La Peak 1 (mM)', laValue: la1, setLa: setLa1 },
        { label: 'Sprint 2 avg power (W) — 10-20s', value: power2, set: setPower2, laLabel: 'La Peak 2 (mM)', laValue: la2, setLa: setLa2 },
        { label: 'Sprint 3 avg power (W) — 20-30s', value: power3, set: setPower3, laLabel: 'La Peak 3 (mM)', laValue: la3, setLa: setLa3 },
      ].map((item, i) => (
        <div key={i} className="space-y-2 border-b border-secondary-muted/20 pb-3">
          <div>
            <label className="text-sm text-white/60 block mb-1">{item.label}</label>
            <input
              type="number" min={0} max={3000} step={1}
              value={item.value}
              onChange={e => item.set(e.target.value)}
              className="w-full px-3 py-2 bg-primary-dark border border-secondary-muted/50 rounded-lg text-white text-center"
            />
          </div>
          <div>
            <label className="text-sm text-white/60 block mb-1">{item.laLabel}</label>
            <input
              type="number" min={0} max={30} step={0.1}
              value={item.laValue}
              onChange={e => item.setLa(e.target.value)}
              className="w-full px-3 py-2 bg-primary-dark border border-secondary-muted/50 rounded-lg text-white text-center"
            />
          </div>
        </div>
      ))}

      {error && <p className="text-sm text-red-400 text-center">{error}</p>}

      <button onClick={handleSubmit} className="btn-primary w-full py-2.5">
        Calculate Results
      </button>
    </div>
  );
}
