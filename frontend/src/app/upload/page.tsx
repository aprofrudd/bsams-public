'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { uploadApi, athletesApi } from '@/lib/api';
import { CsvPreviewTable } from '@/components/CsvPreviewTable';
import { Spinner } from '@/components/Spinner';
import type { Athlete, UploadResult } from '@/lib/types';

type UploadStep = 'select' | 'preview' | 'uploading' | 'results';
type ClearState = 'idle' | 'confirming' | 'clearing';

interface PreviewData {
  warnings: string[];
  events_preview: Array<{
    event_date: string;
    metrics: Record<string, string | number | undefined>;
    athlete_name?: string;
  }>;
  total_events: number;
  errors: Array<{ row: number; reason: string }>;
}

export default function UploadPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  const [step, setStep] = useState<UploadStep>('select');
  const [file, setFile] = useState<File | null>(null);
  const [athletes, setAthletes] = useState<Athlete[]>([]);
  const [selectedAthleteId, setSelectedAthleteId] = useState<string>('');
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingAthletes, setLoadingAthletes] = useState(true);
  const [dragging, setDragging] = useState(false);
  const [clearState, setClearState] = useState<ClearState>('idle');
  const [clearResult, setClearResult] = useState<{ deleted_athletes: number; deleted_events: number } | null>(null);
  const [clearPassword, setClearPassword] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auth guard
  useEffect(() => {
    if (!loading && !user) {
      router.replace('/login');
    }
  }, [loading, user, router]);

  // Load athletes for dropdown
  useEffect(() => {
    async function loadAthletes() {
      try {
        const data = await athletesApi.list();
        setAthletes(data);
      } catch {
        // Non-fatal — dropdown will be empty
      } finally {
        setLoadingAthletes(false);
      }
    }
    if (user) loadAthletes();
  }, [user]);

  const handleFileSelect = useCallback(async (selectedFile: File) => {
    setFile(selectedFile);
    setError(null);
    setStep('preview');

    try {
      const data = await uploadApi.previewCsv(selectedFile);
      setPreviewData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Preview failed');
      setStep('select');
      setFile(null);
    }
  }, []);

  const handleUpload = useCallback(async () => {
    if (!file) return;
    setStep('uploading');
    setError(null);

    try {
      const result = await uploadApi.uploadCsv(
        file,
        selectedAthleteId || undefined
      );
      setUploadResult(result);
      setStep('results');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
      setStep('preview');
    }
  }, [file, selectedAthleteId]);

  const handleReset = useCallback(() => {
    setStep('select');
    setFile(null);
    setPreviewData(null);
    setUploadResult(null);
    setError(null);
    setSelectedAthleteId('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  }, []);

  const handleClearAll = useCallback(async () => {
    if (!clearPassword) {
      setError('Please enter your password to confirm deletion');
      return;
    }
    setClearState('clearing');
    setClearResult(null);
    try {
      const result = await athletesApi.deleteAll(clearPassword);
      setClearResult(result);
      setClearPassword('');
      // Refresh athletes list
      const data = await athletesApi.list();
      setAthletes(data);
      setSelectedAthleteId('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to clear data');
      setClearPassword('');
    } finally {
      setClearState('idle');
    }
  }, [clearPassword]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile?.name.endsWith('.csv')) {
      handleFileSelect(droppedFile);
    } else {
      setError('Please select a CSV file');
    }
  };

  if (loading || !user) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <p className="text-white/60">Loading...</p>
      </div>
    );
  }

  if (user.role !== 'admin' && user.role !== 'coach') {
    router.replace('/training');
    return null;
  }

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="section-title text-2xl mb-6">Upload CSV</h1>

      {error && (
        <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-3 mb-4">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {/* Step 1: File Selection */}
      {step === 'select' && (
        <div className="card">
          <div
            className={`border-2 border-dashed rounded-lg p-4 sm:p-8 text-center cursor-pointer transition-colors ${
              dragging
                ? 'border-accent bg-accent/5'
                : 'border-secondary-muted hover:border-accent active:border-accent active:bg-accent/5'
            }`}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <p className="text-white/60 mb-2">
              Drag and drop a CSV file here, or click to browse
            </p>
            <p className="text-white/40 text-sm">
              Accepted format: .csv with DD/MM/YYYY dates
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleFileSelect(f);
              }}
            />
          </div>

          <div className="mt-4">
            <label className="block text-sm text-white/80 mb-1">
              Assign to athlete (optional)
            </label>
            <select
              className="select w-full"
              value={selectedAthleteId}
              onChange={(e) => setSelectedAthleteId(e.target.value)}
              disabled={loadingAthletes}
            >
              <option value="">Use &quot;Athlete&quot; column from CSV</option>
              {athletes.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
            <p className="text-white/40 text-xs mt-1">
              Leave blank if your CSV has an &quot;Athlete&quot; column
            </p>
          </div>
        </div>
      )}

      {/* Step 2: Preview (loading) */}
      {step === 'preview' && !previewData && (
        <div className="card">
          <Spinner message="Previewing..." />
        </div>
      )}

      {/* Step 2: Preview (data loaded) */}
      {step === 'preview' && previewData && (
        <div className="card">
          <p className="text-white mb-3">
            Found{' '}
            <span className="text-accent font-semibold">
              {previewData.total_events}
            </span>{' '}
            event(s)
            {file && (
              <span className="text-white/40 text-sm ml-2">from {file.name}</span>
            )}
            {previewData.errors.length > 0 && (
              <span className="text-red-400">
                {' '}
                with {previewData.errors.length} error(s)
              </span>
            )}
          </p>

          {previewData.warnings.length > 0 && (
            <div className="bg-yellow-500/10 border border-yellow-500/50 rounded-lg p-3 mb-4">
              <p className="text-yellow-400 text-sm font-medium mb-1">Warnings:</p>
              <ul className="list-disc list-inside text-yellow-400/80 text-sm">
                {previewData.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {previewData.events_preview.length > 0 && (
            <CsvPreviewTable events={previewData.events_preview} />
          )}

          {previewData.total_events > 10 && (
            <p className="text-white/40 text-sm mt-2">
              Showing first 10 of {previewData.total_events} events
            </p>
          )}

          {previewData.errors.length > 0 && (
            <div className="mt-4 bg-red-500/10 border border-red-500/50 rounded-lg p-3">
              <p className="text-red-400 text-sm font-medium mb-1">Errors:</p>
              <ul className="list-disc list-inside text-red-400/80 text-sm max-h-32 overflow-y-auto">
                {previewData.errors.map((e, i) => (
                  <li key={i}>
                    Row {e.row}: {e.reason}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex gap-3 mt-6">
            <button
              className="btn-primary disabled:opacity-50"
              disabled={previewData.total_events === 0}
              onClick={handleUpload}
            >
              Upload {previewData.total_events} Event(s)
            </button>
            <button className="btn-secondary" onClick={handleReset}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Uploading */}
      {step === 'uploading' && (
        <div className="card">
          <Spinner message="Uploading..." />
        </div>
      )}

      {/* Step 4: Results */}
      {step === 'results' && uploadResult && (
        <div className="card">
          <div className="bg-green-500/10 border border-green-500/50 rounded-lg p-4 mb-4">
            <p className="text-green-400 font-semibold">
              Successfully uploaded {uploadResult.processed} event(s)
            </p>
          </div>

          {uploadResult.errors.length > 0 && (
            <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-3 mb-4">
              <p className="text-red-400 text-sm font-medium mb-1">
                {uploadResult.errors.length} error(s):
              </p>
              <ul className="list-disc list-inside text-red-400/80 text-sm">
                {uploadResult.errors.map((e, i) => (
                  <li key={i}>
                    Row {e.row}: {e.reason}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex gap-3">
            <button className="btn-primary" onClick={handleReset}>
              Upload Another
            </button>
            <button
              className="btn-secondary"
              onClick={() => router.push('/testing')}
            >
              View Testing
            </button>
          </div>
        </div>
      )}

      {/* Clear All Data */}
      <div className="card mt-8 border border-red-500/20">
        <h2 className="text-lg font-semibold text-white mb-2">Clear All Data</h2>
        <p className="text-white/60 text-sm mb-4">
          Remove all athletes and performance events. This cannot be undone.
        </p>

        {clearResult && (
          <div className="bg-green-500/10 border border-green-500/50 rounded-lg p-3 mb-4">
            <p className="text-green-400 text-sm">
              Cleared {clearResult.deleted_athletes} athlete(s) and{' '}
              {clearResult.deleted_events} event(s).
            </p>
          </div>
        )}

        {clearState === 'confirming' ? (
          <div className="flex flex-col gap-3">
            <p className="text-red-400 text-sm">Enter your password to confirm deletion:</p>
            <input
              type="password"
              value={clearPassword}
              onChange={(e) => setClearPassword(e.target.value)}
              placeholder="Current password"
              className="input max-w-xs"
              autoComplete="current-password"
            />
            <div className="flex flex-row items-center gap-3">
              <button
                className="px-4 py-2.5 min-h-[44px] bg-red-600 hover:bg-red-700 active:bg-red-800 text-white text-sm rounded-lg transition-colors disabled:opacity-50"
                onClick={handleClearAll}
                disabled={!clearPassword}
              >
                Yes, delete everything
              </button>
              <button
                className="btn-secondary text-sm"
                onClick={() => { setClearState('idle'); setClearPassword(''); }}
              >
                Cancel
              </button>
            </div>
          </div>
        ) : clearState === 'clearing' ? (
          <Spinner message="Clearing data..." />
        ) : (
          <button
            className="px-4 py-2.5 min-h-[44px] border border-red-500/50 text-red-400 hover:bg-red-500/10 active:bg-red-500/20 text-sm rounded-lg transition-colors"
            onClick={() => {
              setClearResult(null);
              setClearState('confirming');
            }}
          >
            Clear All Data
          </button>
        )}
      </div>
    </div>
  );
}
