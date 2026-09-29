'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { authApi } from '@/lib/api';

export default function ResetPasswordPage() {
  const [token, setToken] = useState<string | null>(null);
  const [code, setCode] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    // PKCE flow: check for ?code= query parameter first
    const urlParams = new URLSearchParams(window.location.search);
    const authCode = urlParams.get('code');
    if (authCode) {
      setCode(authCode);
      // Clear query string from URL to prevent code exposure
      window.history.replaceState(null, '', window.location.pathname);
      return;
    }

    // Implicit flow: check for #access_token=...&type=recovery in hash
    const hash = window.location.hash;
    if (hash) {
      const params = new URLSearchParams(hash.substring(1));
      const accessToken = params.get('access_token');
      const type = params.get('type');
      if (accessToken && type === 'recovery') {
        setToken(accessToken);
      }
      // Clear hash from URL to prevent token exposure in browser history
      window.history.replaceState(null, '', window.location.pathname);
    }
  }, []);

  const validatePassword = (pwd: string): string | null => {
    if (pwd.length < 8) return 'Password must be at least 8 characters';
    if (!/[A-Z]/.test(pwd)) return 'Password must contain at least one uppercase letter';
    if (!/\d/.test(pwd)) return 'Password must contain at least one digit';
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    const validationError = validatePassword(newPassword);
    if (validationError) {
      setError(validationError);
      return;
    }

    if (!token && !code) {
      setError('Invalid or expired reset link');
      return;
    }

    setSubmitting(true);
    try {
      await authApi.resetPassword(newPassword, token, code);
      setSuccess(true);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Password reset failed';
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  if (success) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="card w-full max-w-md text-center">
          <div className="mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-12 h-12 text-green-400 mx-auto">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clipRule="evenodd" />
            </svg>
          </div>
          <h2 className="section-title text-xl mb-2">Password Reset Successfully</h2>
          <p className="text-white/60 text-sm mb-6">You can now log in with your new password.</p>
          <Link href="/login" className="btn-primary inline-block px-8">
            Go to Login
          </Link>
        </div>
      </div>
    );
  }

  if (!token && !code) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="card w-full max-w-md text-center">
          <h2 className="section-title text-xl mb-2">Invalid Reset Link</h2>
          <p className="text-white/60 text-sm mb-6">
            This password reset link is invalid or has expired. Please request a new one.
          </p>
          <Link href="/login" className="btn-primary inline-block px-8">
            Back to Login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="card w-full max-w-md">
        <div className="text-center mb-6">
          <h2 className="section-title text-2xl">Reset Password</h2>
          <p className="text-white/60 text-sm mt-1">Enter your new password below.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="new-password" className="block text-sm text-white/80 mb-1">
              New Password
            </label>
            <input
              id="new-password"
              type="password"
              required
              minLength={8}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="input w-full"
              placeholder="At least 8 characters"
            />
          </div>

          <div>
            <label htmlFor="confirm-password" className="block text-sm text-white/80 mb-1">
              Confirm Password
            </label>
            <input
              id="confirm-password"
              type="password"
              required
              minLength={8}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="input w-full"
              placeholder="Re-enter your new password"
            />
          </div>

          <p className="text-white/40 text-xs">
            Must be at least 8 characters with 1 uppercase letter and 1 digit.
          </p>

          {error && (
            <p className="text-red-400 text-sm">{error}</p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="btn-primary w-full disabled:opacity-50"
          >
            {submitting ? 'Resetting...' : 'Reset Password'}
          </button>
        </form>
      </div>
    </div>
  );
}
