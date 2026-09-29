'use client';

import { useState, useRef } from 'react';
import { lactateApi } from '@/lib/api';
import type { GasAnalysisPreview } from '@/lib/types';

interface GasAnalysisUploadProps {
  testId: string;
  testType: 'running' | 'cycling';
  onUploaded: () => void;
  onClose: () => void;
}

export function GasAnalysisUpload({ testId, testType, onUploaded, onClose }: GasAnalysisUploadProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<GasAnalysisPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Protocol config
  const [stageDuration, setStageDuration] = useState('180');
  const [restDuration, setRestDuration] = useState('60');
  const [restStart, setRestStart] = useState('60');
  const [averaging, setAveraging] = useState<'last_60s' | 'full_stage'>('last_60s');

  async function handlePreview() {
    if (!file) return;
    setLoading(true);
    setError(null);
    setPreview(null);
    try {
      const result = await lactateApi.previewGasAnalysis(testId, file, {
        stage_duration_seconds: Number(stageDuration),
        rest_duration_seconds: Number(restDuration),
        rest_start_seconds: Number(restStart),
        averaging_method: averaging,
      });
      setPreview(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Preview failed');
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    if (!file) return;
    setSaving(true);
    setError(null);
    try {
      await lactateApi.uploadGasAnalysis(testId, file, {
        stage_duration_seconds: Number(stageDuration),
        rest_duration_seconds: Number(restDuration),
        rest_start_seconds: Number(restStart),
        averaging_method: averaging,
      });
      onUploaded();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setSaving(false);
    }
  }

  const unitLabel = testType === 'running' ? 'km/h' : 'W';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="bg-primary-dark border border-secondary-muted/50 rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto mx-4 p-5 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-heading text-white">Upload Gas Analysis (CPET)</h3>
          <button onClick={onClose} className="text-white/40 hover:text-white p-2 min-h-[44px] min-w-[44px]">
            &times;
          </button>
        </div>

        {/* File picker */}
        <div>
          <label className="text-sm text-white/60 block mb-1">File (.xlsx or .csv)</label>
          <input
            ref={fileRef}
            type="file"
            accept=".xlsx,.csv"
            onChange={(e) => {
              setFile(e.target.files?.[0] || null);
              setPreview(null);
              setError(null);
            }}
            className="input w-full text-sm file:mr-3 file:py-1 file:px-3 file:rounded file:border-0 file:bg-accent/20 file:text-accent file:cursor-pointer"
          />
        </div>

        {/* Protocol config (shown for running tests) */}
        {testType === 'running' && (
          <div className="border border-secondary-muted/30 rounded p-3 space-y-2">
            <p className="text-xs text-white/40 font-medium">Protocol Config (Running)</p>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="text-xs text-white/40">Rest Start (s)</label>
                <input
                  type="number"
                  value={restStart}
                  onChange={(e) => setRestStart(e.target.value)}
                  className="input w-full text-sm"
                />
              </div>
              <div>
                <label className="text-xs text-white/40">Stage Duration (s)</label>
                <input
                  type="number"
                  value={stageDuration}
                  onChange={(e) => setStageDuration(e.target.value)}
                  className="input w-full text-sm"
                />
              </div>
              <div>
                <label className="text-xs text-white/40">Rest Duration (s)</label>
                <input
                  type="number"
                  value={restDuration}
                  onChange={(e) => setRestDuration(e.target.value)}
                  className="input w-full text-sm"
                />
              </div>
            </div>
          </div>
        )}

        {/* Averaging method */}
        <div>
          <label className="text-xs text-white/40 block mb-1">Averaging Method</label>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setAveraging('last_60s')}
              className={`text-xs px-3 py-1.5 rounded border transition-colors ${
                averaging === 'last_60s'
                  ? 'bg-accent/20 border-accent text-accent'
                  : 'border-secondary-muted/50 text-white/40 hover:text-white/60'
              }`}
            >
              Last 60s (steady-state)
            </button>
            <button
              type="button"
              onClick={() => setAveraging('full_stage')}
              className={`text-xs px-3 py-1.5 rounded border transition-colors ${
                averaging === 'full_stage'
                  ? 'bg-accent/20 border-accent text-accent'
                  : 'border-secondary-muted/50 text-white/40 hover:text-white/60'
              }`}
            >
              Full Stage
            </button>
          </div>
        </div>

        {/* Preview button */}
        <button
          type="button"
          onClick={handlePreview}
          disabled={!file || loading}
          className="btn-primary text-sm px-4 py-1.5 w-full disabled:opacity-50"
        >
          {loading ? 'Parsing...' : 'Preview'}
        </button>

        {error && <p className="text-red-400 text-sm">{error}</p>}

        {/* Preview results */}
        {preview && (
          <div className="space-y-3">
            <div className="flex flex-wrap gap-3 text-xs">
              <span className="text-white/60">
                Interval: <span className="text-white">{preview.interval_seconds}s</span>
              </span>
              <span className="text-white/60">
                Stages: <span className="text-white">{preview.stage_count}</span>
              </span>
              <span className="text-white/60">
                Samples: <span className="text-white">{preview.sample_count}</span>
              </span>
              <span className="text-white/60">
                Columns: <span className="text-white">{preview.columns_detected.join(', ')}</span>
              </span>
            </div>

            {preview.fat_max && (
              <div className="bg-orange-500/10 border border-orange-500/30 rounded p-2 text-sm">
                <span className="text-orange-400 font-medium">Fat Max: </span>
                <span className="text-white">
                  {preview.fat_max.max_fat_oxidation_gh} g/h
                  {preview.fat_max.fat_max_intensity != null && (
                    <> at {preview.fat_max.fat_max_intensity} {unitLabel}</>
                  )}
                </span>
              </div>
            )}

            {/* Stage averages table */}
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-white/40">
                    <th className="text-left py-1 pr-2">#</th>
                    <th className="text-right py-1 px-2">{unitLabel}</th>
                    <th className="text-right py-1 px-2">VO2</th>
                    <th className="text-right py-1 px-2">RER</th>
                    <th className="text-right py-1 px-2">VE</th>
                    <th className="text-right py-1 px-2">HR</th>
                    <th className="text-right py-1 px-2">FAT</th>
                    <th className="text-right py-1 px-2">CHO</th>
                    <th className="text-right py-1 pl-2">Pts</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.stage_averages.map((sa) => (
                    <tr key={sa.stage_number} className="border-t border-secondary-muted/20">
                      <td className="py-1 pr-2 text-white/60">{sa.stage_number}</td>
                      <td className="py-1 px-2 text-right text-white">
                        {sa.intensity_value ?? '-'}
                      </td>
                      <td className="py-1 px-2 text-right text-white/80">
                        {sa.avg_vo2_ml_kg_min?.toFixed(1) ?? sa.avg_vo2_l_min?.toFixed(2) ?? '-'}
                      </td>
                      <td className="py-1 px-2 text-right text-white/80">
                        {sa.avg_rer?.toFixed(2) ?? '-'}
                      </td>
                      <td className="py-1 px-2 text-right text-white/80">
                        {sa.avg_ve_l_min?.toFixed(1) ?? '-'}
                      </td>
                      <td className="py-1 px-2 text-right text-white/80">
                        {sa.avg_hr_bpm?.toFixed(0) ?? '-'}
                      </td>
                      <td className="py-1 px-2 text-right text-orange-400">
                        {sa.avg_fat_gh?.toFixed(1) ?? '-'}
                      </td>
                      <td className="py-1 px-2 text-right text-lime-400">
                        {sa.avg_cho_gh?.toFixed(1) ?? '-'}
                      </td>
                      <td className="py-1 pl-2 text-right text-white/40">
                        {sa.data_point_count}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Save button */}
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="btn-primary text-sm px-4 py-1.5 w-full disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Gas Analysis'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
