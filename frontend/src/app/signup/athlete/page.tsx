'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { invitationsApi, fetchApi } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import type { InvitationValidateResponse } from '@/lib/types';

function AthleteSignupForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { signupAthlete } = useAuth();
  const code = searchParams.get('code') || '';

  const [validation, setValidation] = useState<InvitationValidateResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [consentChecked, setConsentChecked] = useState(false);

  useEffect(() => {
    if (!code) {
      setLoading(false);
      return;
    }
    invitationsApi.validate(code)
      .then(setValidation)
      .catch(() => setValidation({ valid: false }))
      .finally(() => setLoading(false));
  }, [code]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    setSubmitting(true);
    try {
      await signupAthlete(email, password, code);
      // Record data processing consent
      try {
        await fetchApi('/user-consents/data_processing', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ granted: true }),
        });
      } catch {
        // Non-blocking — consent gate will catch it on next load
      }
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Signup failed');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <p className="text-white/60">Validating invitation...</p>
      </div>
    );
  }

  if (!code || !validation?.valid) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="card max-w-md w-full text-center">
          <h1 className="section-title text-2xl mb-4">Invalid Invitation</h1>
          <p className="text-white/40">This invitation link is invalid, expired, or has already been used.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="card w-full max-w-md">
        <div className="text-center mb-6">
          <h2 className="section-title text-2xl">Athlete Signup</h2>
          <p className="text-white/60 text-sm mt-2">
            You&apos;ve been invited to join as{' '}
            <span className="text-white font-semibold">{validation.athlete_first_name}</span>
          </p>
        </div>

        {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="athlete-email" className="block text-sm text-white/80 mb-1">Email</label>
            <input
              id="athlete-email"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              className="input w-full"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label htmlFor="athlete-password" className="block text-sm text-white/80 mb-1">Password</label>
            <input
              id="athlete-password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              minLength={8}
              className="input w-full"
              placeholder="At least 8 characters"
            />
          </div>
          <div>
            <label htmlFor="athlete-confirm" className="block text-sm text-white/80 mb-1">Confirm Password</label>
            <input
              id="athlete-confirm"
              type="password"
              value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)}
              required
              className="input w-full"
              placeholder="Re-enter password"
            />
          </div>
          <label className="flex items-start gap-2 text-sm text-white/80">
            <input
              type="checkbox"
              checked={consentChecked}
              onChange={(e) => setConsentChecked(e.target.checked)}
              className="mt-0.5 accent-accent"
              required
            />
            <span>
              I agree to the{' '}
              <a href="/privacy" target="_blank" className="text-accent hover:underline">Privacy Policy</a>
              {' '}and{' '}
              <a href="/terms" target="_blank" className="text-accent hover:underline">Terms of Service</a>
              {' '}and consent to the processing of my health and fitness data.
            </span>
          </label>
          <button
            type="submit"
            disabled={submitting}
            className="btn-primary w-full disabled:opacity-50"
          >
            {submitting ? 'Creating Account...' : 'Create Account'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function AthleteSignupPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-[60vh]">
        <p className="text-white/60">Loading...</p>
      </div>
    }>
      <AthleteSignupForm />
    </Suspense>
  );
}
