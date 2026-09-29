'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { authApi, fetchApi } from '@/lib/api';
import { safeNextPath } from '@/lib/safeNextPath';

export default function LoginPage() {
  const router = useRouter();
  const { login, signup, user, loading, reconnecting, retryAuth } = useAuth();

  const [mode, setMode] = useState<'login' | 'signup' | 'forgot'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [consentChecked, setConsentChecked] = useState(false);

  // Where to go after signing in, read once per mount so the render-time redirect
  // below sees it too.
  const [nextPath] = useState<string | null>(() =>
    typeof window === 'undefined' ? null : safeNextPath(window.location.search)
  );

  // Intercept Supabase password recovery redirects that land on /login
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    if (code) {
      router.replace(`/reset-password?code=${encodeURIComponent(code)}`);
      return;
    }
    const hash = window.location.hash;
    if (hash && hash.includes('type=recovery')) {
      router.replace(`/reset-password${hash}`);
    }
  }, [router]);

  // Redirect if already logged in
  if (!loading && user) {
    router.replace(nextPath ?? '/');
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccessMessage('');
    setSubmitting(true);

    try {
      if (mode === 'forgot') {
        await authApi.forgotPassword(email);
        setSuccessMessage('If an account with that email exists, a password reset link has been sent.');
        return;
      }
      if (mode === 'login') {
        await login(email, password);
      } else {
        await signup(email, password);
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
      }
      router.replace(nextPath ?? '/');
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Something went wrong';
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  // Session restore gave up. The cookie is still valid — the backend just isn't
  // answering (decision 85 turns a Supabase blip into a 503), so asking a station
  // operator for the shared admin password here would be useless as well as exactly
  // what a lookalike login page wants. Offer a retry instead of the form.
  if (reconnecting) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="card w-full max-w-md text-center">
          <h2 className="section-title text-xl">Reconnecting</h2>
          <p className="text-white/60 text-sm mt-2">
            Can&apos;t reach the server. You are still signed in — this retries by itself
            when the connection comes back.
          </p>
          <button type="button" onClick={retryAuth} className="btn-primary mt-4">
            Try again
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <p className="text-white/60">Loading...</p>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="card w-full max-w-md">
        <div className="text-center mb-6">
          <h2 className="section-title text-2xl">BSAMS</h2>
          <p className="text-white/60 text-sm mt-1">
            Boxing Science Athlete Management
          </p>
        </div>

        {successMessage && (
          <div className="bg-green-500/10 border border-green-500/30 rounded-lg px-4 py-3 mb-4">
            <p className="text-green-400 text-sm">{successMessage}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm text-white/80 mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input w-full"
              placeholder="you@example.com"
            />
          </div>

          {mode !== 'forgot' && (
            <div>
              <label
                htmlFor="password"
                className="block text-sm text-white/80 mb-1"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input w-full"
                placeholder="At least 8 characters (with uppercase and number)"
              />
              {mode === 'login' && (
                <button
                  type="button"
                  onClick={() => {
                    setMode('forgot');
                    setError('');
                    setSuccessMessage('');
                  }}
                  className="text-accent hover:underline text-xs mt-1"
                >
                  Forgot password?
                </button>
              )}
            </div>
          )}

          {mode === 'signup' && (
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
          )}

          {error && (
            <p className="text-red-400 text-sm">{error}</p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="btn-primary w-full disabled:opacity-50"
          >
            {submitting
              ? 'Please wait...'
              : mode === 'forgot'
                ? 'Send Reset Link'
                : mode === 'login'
                  ? 'Log In'
                  : 'Sign Up'}
          </button>
        </form>

        <p className="text-center text-sm text-white/60 mt-4">
          {mode === 'forgot' ? (
            <button
              type="button"
              onClick={() => {
                setMode('login');
                setError('');
                setSuccessMessage('');
              }}
              className="text-accent hover:underline"
            >
              Back to Login
            </button>
          ) : mode === 'login' ? (
            <>
              Don&apos;t have an account?{' '}
              <button
                type="button"
                onClick={() => {
                  setMode('signup');
                  setError('');
                }}
                className="text-accent hover:underline"
              >
                Sign Up
              </button>
            </>
          ) : (
            <>
              Already have an account?{' '}
              <button
                type="button"
                onClick={() => {
                  setMode('login');
                  setError('');
                }}
                className="text-accent hover:underline"
              >
                Log In
              </button>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
