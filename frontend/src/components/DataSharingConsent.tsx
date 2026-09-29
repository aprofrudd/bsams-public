'use client';

import { useState, useEffect } from 'react';
import { consentApi } from '@/lib/api';

export function DataSharingConsent() {
  const [enabled, setEnabled] = useState(false);
  const [infoText, setInfoText] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showConfirm, setShowConfirm] = useState(false);
  const [showInfo, setShowInfo] = useState(false);

  useEffect(() => {
    loadConsent();
  }, []);

  async function loadConsent() {
    try {
      setIsLoading(true);
      const data = await consentApi.get();
      setEnabled(data.data_sharing_enabled);
      setInfoText(data.info_text);
    } catch {
      setError('Failed to load consent status');
    } finally {
      setIsLoading(false);
    }
  }

  async function handleToggle() {
    if (!enabled) {
      setShowConfirm(true);
      return;
    }
    await saveConsent(false);
  }

  async function saveConsent(newValue: boolean) {
    try {
      setIsSaving(true);
      setError(null);
      const data = await consentApi.update(newValue);
      setEnabled(data.data_sharing_enabled);
      setShowConfirm(false);
    } catch {
      setError('Failed to update consent');
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) return null;

  return (
    <>
      <div className="flex items-center gap-2">
        {/* Toggle switch */}
        <button
          onClick={handleToggle}
          disabled={isSaving}
          aria-label={`Data sharing ${enabled ? 'enabled' : 'disabled'}`}
          role="switch"
          aria-checked={enabled}
          className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors duration-200 disabled:opacity-50 ${
            enabled ? 'bg-green-500' : 'bg-white/20'
          }`}
        >
          <span
            className={`inline-block h-4 w-4 rounded-full bg-white shadow transition-transform duration-200 ${
              enabled ? 'translate-x-[18px]' : 'translate-x-[2px]'
            }`}
          />
        </button>

        <span className="text-xs text-white/40 select-none">
          Data Sharing
        </span>

        <button
          onClick={() => setShowInfo(true)}
          className="text-xs text-white/30 hover:text-white/50 underline transition-colors"
        >
          Learn more
        </button>

        {error && <span className="text-red-400 text-xs">!</span>}
      </div>

      {/* Confirmation dialog (enable flow) */}
      {showConfirm && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowConfirm(false);
          }}
        >
          <div className="card w-full max-w-sm mx-4">
            <h3 className="section-title text-base mb-3">Confirm Data Sharing</h3>
            <p className="text-white/60 text-sm mb-4">{infoText}</p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowConfirm(false)}
                className="btn-secondary flex-1"
              >
                Cancel
              </button>
              <button
                onClick={() => saveConsent(true)}
                disabled={isSaving}
                className="btn-primary flex-1 disabled:opacity-50"
              >
                {isSaving ? 'Enabling...' : 'I Agree'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Info dialog (learn more) */}
      {showInfo && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowInfo(false);
          }}
        >
          <div className="card w-full max-w-sm mx-4">
            <h3 className="section-title text-base mb-3">About Data Sharing</h3>
            <p className="text-white/60 text-sm mb-4">{infoText}</p>
            <button
              onClick={() => setShowInfo(false)}
              className="btn-secondary w-full"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </>
  );
}
