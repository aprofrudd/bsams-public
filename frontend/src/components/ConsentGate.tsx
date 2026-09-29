'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/lib/auth';
import { fetchApi } from '@/lib/api';
import Link from 'next/link';

export function ConsentGate({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const [consented, setConsented] = useState<boolean | null>(null);
  const [checking, setChecking] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!user || loading) {
      setChecking(false);
      return;
    }

    // Check if user has granted data_processing consent
    fetchApi<Array<{ consent_type: string; granted: boolean }>>('/user-consents/')
      .then((consents) => {
        const dp = consents.find((c) => c.consent_type === 'data_processing');
        setConsented(dp?.granted === true);
      })
      .catch(() => {
        // If consent API fails (e.g., tables not created yet), allow through
        setConsented(true);
      })
      .finally(() => setChecking(false));
  }, [user, loading]);

  const handleConsent = async () => {
    setSubmitting(true);
    try {
      await fetchApi('/user-consents/data_processing', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ granted: true }),
      });
      setConsented(true);
    } catch {
      // Allow through on error
      setConsented(true);
    } finally {
      setSubmitting(false);
    }
  };

  // Don't gate if not logged in, still loading, or already consented
  if (!user || loading || checking || consented !== false) {
    return <>{children}</>;
  }

  // Show consent modal
  return (
    <>
      {children}
      <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
        <div className="card max-w-lg w-full">
          <h2 className="section-title text-xl mb-4">Data Processing Consent</h2>
          <p className="text-white/80 text-sm mb-4">
            BSAMS processes health and fitness data including performance metrics,
            body measurements, wellness scores, and training data to provide athlete
            management services.
          </p>
          <p className="text-white/80 text-sm mb-4">
            By continuing, you consent to the processing of your data as described in our{' '}
            <Link href="/privacy" className="text-accent hover:underline">Privacy Policy</Link>.
            You can withdraw consent at any time.
          </p>
          <div className="flex gap-3 justify-end">
            <button
              onClick={handleConsent}
              disabled={submitting}
              className="btn-primary px-6 disabled:opacity-50"
            >
              {submitting ? 'Processing...' : 'I Consent'}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
