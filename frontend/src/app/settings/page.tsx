'use client';

import { useState } from 'react';
import { useAuth } from '@/lib/auth';
import { authApi } from '@/lib/api';
import { useRouter } from 'next/navigation';

export default function SettingsPage() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  // Change password state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [passwordSubmitting, setPasswordSubmitting] = useState(false);

  // Change email state
  const [emailPassword, setEmailPassword] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [emailError, setEmailError] = useState('');
  const [emailSubmitting, setEmailSubmitting] = useState(false);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <p className="text-white/60">Loading...</p>
      </div>
    );
  }

  if (!user) {
    router.replace('/login');
    return null;
  }

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError('');

    if (newPassword !== confirmNewPassword) {
      setPasswordError('New passwords do not match');
      return;
    }

    if (newPassword.length < 8) {
      setPasswordError('Password must be at least 8 characters');
      return;
    }
    if (!/[A-Z]/.test(newPassword)) {
      setPasswordError('Password must contain at least one uppercase letter');
      return;
    }
    if (!/\d/.test(newPassword)) {
      setPasswordError('Password must contain at least one digit');
      return;
    }

    setPasswordSubmitting(true);
    try {
      await authApi.changePassword(currentPassword, newPassword);
      await logout();
      router.replace('/login');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Password change failed';
      setPasswordError(message);
      setPasswordSubmitting(false);
    }
  };

  const handleChangeEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    setEmailError('');

    setEmailSubmitting(true);
    try {
      await authApi.changeEmail(emailPassword, newEmail);
      await logout();
      router.replace('/login');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Email change failed';
      setEmailError(message);
      setEmailSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="section-title text-2xl">Account Settings</h1>

      {/* Change Password */}
      <div className="card">
        <h2 className="section-title text-base sm:text-lg mb-4">Change Password</h2>
        <form onSubmit={handleChangePassword} className="space-y-4">
          <div>
            <label htmlFor="current-password" className="block text-sm text-white/80 mb-1">
              Current Password
            </label>
            <input
              id="current-password"
              type="password"
              required
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="input w-full"
            />
          </div>
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
            />
          </div>
          <div>
            <label htmlFor="confirm-new-password" className="block text-sm text-white/80 mb-1">
              Confirm New Password
            </label>
            <input
              id="confirm-new-password"
              type="password"
              required
              minLength={8}
              value={confirmNewPassword}
              onChange={(e) => setConfirmNewPassword(e.target.value)}
              className="input w-full"
            />
          </div>
          <p className="text-white/40 text-xs">
            Must be at least 8 characters with 1 uppercase letter and 1 digit.
          </p>

          {passwordError && <p className="text-red-400 text-sm">{passwordError}</p>}

          <button
            type="submit"
            disabled={passwordSubmitting}
            className="btn-primary disabled:opacity-50"
          >
            {passwordSubmitting ? 'Updating...' : 'Update Password'}
          </button>
        </form>
      </div>

      {/* Change Email */}
      <div className="card">
        <h2 className="section-title text-base sm:text-lg mb-4">Change Email</h2>
        <form onSubmit={handleChangeEmail} className="space-y-4">
          <div>
            <label className="block text-sm text-white/80 mb-1">Current Email</label>
            <div className="input w-full bg-white/5 text-white/60 cursor-not-allowed">
              {user.email || 'Not available'}
            </div>
          </div>
          <div>
            <label htmlFor="new-email" className="block text-sm text-white/80 mb-1">
              New Email
            </label>
            <input
              id="new-email"
              type="email"
              required
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              className="input w-full"
              placeholder="new@example.com"
            />
          </div>
          <div>
            <label htmlFor="email-password" className="block text-sm text-white/80 mb-1">
              Current Password
            </label>
            <input
              id="email-password"
              type="password"
              required
              value={emailPassword}
              onChange={(e) => setEmailPassword(e.target.value)}
              className="input w-full"
              placeholder="Verify your identity"
            />
          </div>

          {emailError && <p className="text-red-400 text-sm">{emailError}</p>}

          <button
            type="submit"
            disabled={emailSubmitting}
            className="btn-primary disabled:opacity-50"
          >
            {emailSubmitting ? 'Updating...' : 'Update Email'}
          </button>
        </form>
      </div>
    </div>
  );
}
