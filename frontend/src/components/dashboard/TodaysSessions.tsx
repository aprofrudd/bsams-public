'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import Link from 'next/link';
import { trainingApi } from '@/lib/api';
import type { TrainingSession } from '@/lib/types';

interface TodaysSessionsProps {
  athleteId: string;
  dataVersion: number;
}

function formatDate(iso: string): string {
  return new Date(iso + 'T00:00:00').toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
  });
}

function SessionCard({ session, showDate }: { session: TrainingSession; showDate?: boolean }) {
  const today = new Date().toISOString().slice(0, 10);
  const isOverdue = session.status === 'assigned' && session.session_date < today;

  const statusLabel =
    isOverdue ? 'Overdue' :
    session.status === 'assigned' ? 'Assigned' :
    session.status === 'completed' ? 'Completed' : 'Logged';

  const statusClasses =
    isOverdue ? 'bg-red-500/20 text-red-400' :
    session.status === 'assigned' ? 'bg-accent/20 text-accent' :
    session.status === 'completed' ? 'bg-green-500/20 text-green-400' :
    'bg-white/10 text-white/50';

  return (
    <div className="bg-secondary-muted/10 rounded-lg px-4 py-3 flex items-center justify-between gap-3">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-white truncate">{session.training_type}</span>
          <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded shrink-0 ${statusClasses}`}>
            {statusLabel}
          </span>
        </div>
        {session.srpe != null && (
          <p className="text-xs text-white/40 mt-1">sRPE: {session.srpe}</p>
        )}
        {session.status === 'assigned' && session.notes && (
          <p className="text-xs text-white/40 mt-1 truncate">{session.notes}</p>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {showDate && (
          <span className="text-xs text-white/30">{formatDate(session.session_date)}</span>
        )}
        {session.status === 'assigned' && (
          <Link
            href="/training"
            className="text-xs font-medium text-accent hover:text-accent/80 transition-colors whitespace-nowrap"
          >
            Complete in My Training &rarr;
          </Link>
        )}
      </div>
    </div>
  );
}

export function TodaysSessions({ athleteId, dataVersion }: TodaysSessionsProps) {
  const [sessions, setSessions] = useState<TrainingSession[]>([]);
  const [loading, setLoading] = useState(true);

  const today = new Date().toISOString().slice(0, 10);

  const startDate = useMemo(() => {
    const d = new Date();
    d.setDate(d.getDate() - 6);
    return d.toISOString().slice(0, 10);
  }, []);

  const loadSessions = useCallback(async () => {
    try {
      setLoading(true);
      const data = await trainingApi.listSessions(athleteId, {
        startDate,
        endDate: today,
      });
      setSessions(data);
    } catch {
      // Silently handle
    } finally {
      setLoading(false);
    }
  }, [athleteId, today, startDate]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions, dataVersion]);

  const todaySessions = sessions.filter((s) => s.session_date === today);
  const recentSessions = sessions
    .filter((s) => s.session_date !== today)
    .sort((a, b) => b.session_date.localeCompare(a.session_date))
    .slice(0, 5);

  if (loading) {
    return (
      <div className="space-y-2">
        <h3 className="section-title text-sm">Today&apos;s Sessions</h3>
        <div className="flex items-center gap-2 text-white/40 text-sm py-4">
          <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          Loading...
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <h3 className="section-title text-sm">Today&apos;s Sessions</h3>

      {todaySessions.length === 0 ? (
        <div className="bg-secondary-muted/10 rounded-lg px-4 py-6 text-center">
          <p className="text-white/40 text-sm">No sessions for today. Log a session or check back later.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {todaySessions.map((session) => (
            <SessionCard key={session.id} session={session} />
          ))}
        </div>
      )}

      {recentSessions.length > 0 && (
        <div className="space-y-2 pt-2">
          <h4 className="text-xs font-semibold text-white/50 uppercase tracking-wider">Recent</h4>
          <div className="space-y-2">
            {recentSessions.map((session) => (
              <SessionCard key={session.id} session={session} showDate />
            ))}
          </div>
        </div>
      )}

      {sessions.length === 0 && (
        <div className="bg-secondary-muted/10 rounded-lg px-4 py-6 text-center">
          <p className="text-white/40 text-sm">No sessions in the last 7 days.</p>
        </div>
      )}

      <div className="pt-1">
        <Link
          href="/training"
          className="text-xs font-medium text-accent hover:text-accent/80 transition-colors"
        >
          View all in My Training &rarr;
        </Link>
      </div>
    </div>
  );
}
