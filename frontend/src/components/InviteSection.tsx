'use client';

import { useState, useEffect } from 'react';
import { invitationsApi } from '@/lib/api';
import type { InvitationResponse, Athlete } from '@/lib/types';

interface InviteSectionProps {
  athlete: Athlete;
}

export default function InviteSection({ athlete }: InviteSectionProps) {
  const [invitation, setInvitation] = useState<InvitationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  const getInviteUrl = (code: string) =>
    `${window.location.origin}/signup/athlete?code=${code}`;

  const handleCopy = async () => {
    if (!invitation) return;
    try {
      await navigator.clipboard.writeText(getInviteUrl(invitation.invite_code));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback: select the link text
    }
  };

  // Check for existing active invitation on mount
  useEffect(() => {
    invitationsApi.list().then(invites => {
      const active = invites.find(
        inv => inv.athlete_id === athlete.id && !inv.used_at && new Date(inv.expires_at) > new Date()
      );
      if (active) setInvitation(active);
    }).catch(() => {});
  }, [athlete.id]);

  const handleGenerate = async () => {
    setLoading(true);
    setError('');
    try {
      const inv = await invitationsApi.create(athlete.id);
      setInvitation(inv);
    } catch (err: any) {
      setError(err.message || 'Failed to generate invitation');
    } finally {
      setLoading(false);
    }
  };

  const handleRevoke = async () => {
    if (!invitation) return;
    try {
      await invitationsApi.revoke(invitation.id);
      setInvitation(null);
    } catch (err: any) {
      setError(err.message || 'Failed to revoke invitation');
    }
  };

  // Athlete already linked
  if (athlete.user_id) {
    return (
      <div className="mt-6 p-4 border border-muted-blue rounded-lg">
        <div className="flex items-center gap-2">
          <span className="text-green-400 text-sm font-semibold">&#10003; Athlete account linked</span>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-6 p-4 border border-muted-blue rounded-lg">
      <h3 className="section-title text-sm mb-3">Athlete Portal Access</h3>
      {error && <p className="text-red-400 text-sm mb-2">{error}</p>}

      {invitation ? (
        <div className="space-y-3">
          <div className="bg-primary-bg p-3 rounded">
            <p className="text-gray-400 text-xs mb-1">Invite Code</p>
            <p className="text-accent text-2xl font-mono font-bold tracking-widest">{invitation.invite_code}</p>
            <p className="text-gray-500 text-xs mt-1">
              Expires: {new Date(invitation.expires_at).toLocaleDateString()}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <a
              href={getInviteUrl(invitation.invite_code)}
              target="_blank"
              rel="noopener noreferrer"
              className="text-accent text-xs underline break-all"
            >
              {getInviteUrl(invitation.invite_code)}
            </a>
            <button
              onClick={handleCopy}
              className="shrink-0 px-2 py-1 text-xs border border-muted-blue rounded hover:border-accent text-gray-400 hover:text-white"
            >
              {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>
          <p className="text-gray-400 text-xs">
            Share this link with the athlete to create their account.
          </p>
          <button
            onClick={handleRevoke}
            className="text-red-400 text-sm hover:text-red-300"
          >
            Revoke Invitation
          </button>
        </div>
      ) : (
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="px-4 py-2 bg-accent text-primary-bg font-semibold rounded text-sm hover:opacity-90 disabled:opacity-50"
        >
          {loading ? 'Generating...' : 'Generate Invite Code'}
        </button>
      )}
    </div>
  );
}
