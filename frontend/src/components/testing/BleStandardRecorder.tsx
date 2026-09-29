'use client';

import { useState, useCallback } from 'react';
import { airBikeRecordingApi } from '@/lib/api';
import type { BleSample } from '@/lib/hooks/useBleRecorder';

const DURATION_OPTIONS = [
  { label: '30s', value: 30 },
  { label: '45s', value: 45 },
  { label: '60s', value: 60 },
  { label: '90s', value: 90 },
  { label: '120s', value: 120 },
  { label: 'Custom', value: -1 },
];

interface BleStandardRecorderProps {
  athleteId: string;
  recorderState: 'idle' | 'countdown' | 'recording' | 'done';
  samples: BleSample[];
  countdown: number;
  elapsed: number;
  remaining: number;
  onStart: (durationSec: number) => void;
  onStop: () => void;
  onReset: () => void;
  onSaved: () => void;
  isConnected: boolean;
}

export function BleStandardRecorder({
  athleteId,
  recorderState,
  samples,
  countdown,
  elapsed,
  remaining,
  onStart,
  onStop,
  onReset,
  onSaved,
  isConnected,
}: BleStandardRecorderProps) {
  const [selectedDuration, setSelectedDuration] = useState(30);
  const [customDuration, setCustomDuration] = useState(30);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const effectiveDuration = selectedDuration === -1 ? customDuration : selectedDuration;

  const handleStart = useCallback(() => {
    if (effectiveDuration < 5 || effectiveDuration > 3600) return;
    onStart(effectiveDuration);
  }, [effectiveDuration, onStart]);

  const handleSave = useCallback(async () => {
    if (samples.length === 0) return;
    setSaving(true);
    setSaveError(null);
    try {
      const today = new Date().toISOString().split('T')[0];
      await airBikeRecordingApi.createRecording(athleteId, {
        test_date: today,
        duration_s: elapsed,
        samples,
        notes: null,
      });
      onSaved();
      onReset();
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Failed to save recording');
    } finally {
      setSaving(false);
    }
  }, [athleteId, elapsed, samples, onSaved, onReset]);

  const handleExportCsv = useCallback(() => {
    if (samples.length === 0) return;
    const headers = 'elapsed_ms,watts,speed_kmh,cadence_rpm,distance_m,calories_kcal';
    const rows = samples.map(s =>
      `${s.elapsed_ms},${s.watts},${s.speed_kmh ?? ''},${s.cadence_rpm ?? ''},${s.distance_m ?? ''},${s.calories_kcal ?? ''}`
    );
    const csv = headers + '\n' + rows.join('\n') + '\n';
    const blob = new Blob([csv], { type: 'text/csv' });
    const ts = new Date().toISOString().replace(/:/g, '-').replace(/\.\d+Z$/, '');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `assault-bike-${ts}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
  }, [samples]);

  return (
    <div className="space-y-3">
      {/* Duration selector */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-white/40">Duration:</span>
        {DURATION_OPTIONS.map(opt => (
          <button
            key={opt.value}
            onClick={() => setSelectedDuration(opt.value)}
            disabled={recorderState === 'recording' || recorderState === 'countdown'}
            className={`text-xs px-2.5 py-1 rounded transition-colors min-h-[32px] ${
              selectedDuration === opt.value
                ? 'bg-accent text-white'
                : 'bg-secondary-muted/30 text-white/50 hover:text-white/80'
            } disabled:opacity-50`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {selectedDuration === -1 && (
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={5}
            max={3600}
            value={customDuration}
            onChange={e => setCustomDuration(Math.max(5, Math.min(3600, parseInt(e.target.value) || 5)))}
            disabled={recorderState === 'recording' || recorderState === 'countdown'}
            className="w-20 px-2 py-1 text-sm bg-primary-dark border border-secondary-muted/50 rounded text-white text-center"
          />
          <span className="text-xs text-white/40">seconds</span>
        </div>
      )}

      {/* Recording status */}
      {recorderState === 'countdown' && (
        <div className="text-center py-4">
          <div className="text-4xl font-bold font-mono text-amber-400">{countdown}</div>
          <div className="text-xs text-white/40 mt-1">Get ready...</div>
        </div>
      )}

      {recorderState === 'recording' && (
        <div className="text-center py-2">
          <div className="text-3xl font-bold font-mono text-red-400">{remaining}s</div>
          <div className="text-xs text-white/40 mt-1">
            {samples.length} sample{samples.length !== 1 ? 's' : ''} captured
          </div>
        </div>
      )}

      {recorderState === 'done' && (
        <div className="text-center py-2">
          <div className="text-sm text-green-400 font-medium">
            Recording complete — {samples.length} samples ({elapsed}s)
          </div>
        </div>
      )}

      {/* Controls */}
      <div className="flex gap-2">
        {recorderState === 'idle' && (
          <button
            onClick={handleStart}
            disabled={!isConnected}
            className="btn-primary text-sm px-4 py-2 flex-1 disabled:opacity-50"
          >
            Start Recording
          </button>
        )}
        {(recorderState === 'recording' || recorderState === 'countdown') && (
          <button
            onClick={onStop}
            className="text-sm px-4 py-2 flex-1 rounded bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors"
          >
            Stop
          </button>
        )}
        {recorderState === 'done' && (
          <>
            <button
              onClick={handleSave}
              disabled={saving || samples.length === 0}
              className="btn-primary text-sm px-4 py-2 flex-1 disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save to BSAMS'}
            </button>
            <button
              onClick={handleExportCsv}
              disabled={samples.length === 0}
              className="text-sm px-4 py-2 rounded bg-secondary-muted/30 text-white/60 hover:text-white hover:bg-secondary-muted/50 transition-colors"
            >
              CSV
            </button>
            <button
              onClick={onReset}
              className="text-sm px-4 py-2 rounded bg-secondary-muted/30 text-white/60 hover:text-white hover:bg-secondary-muted/50 transition-colors"
            >
              Reset
            </button>
          </>
        )}
      </div>

      {saveError && <p className="text-xs text-red-400">{saveError}</p>}
    </div>
  );
}
