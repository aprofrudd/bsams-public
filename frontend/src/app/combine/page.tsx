'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { combineApi, ApiError } from '@/lib/api';
import type { CombineEventListItem } from '@/lib/types';

const STATUS_STYLES: Record<string, string> = {
  draft: 'bg-secondary-muted/30 text-white/60',
  live: 'bg-green-500/20 text-green-300',
  closed: 'bg-white/10 text-white/40',
};

export default function CombineListPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const [events, setEvents] = useState<CombineEventListItem[]>([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [eventDate, setEventDate] = useState('');
  const [venue, setVenue] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (loading) return;
    // Come back here after signing in — a station iPad that lands on /training has
    // to be navigated back by hand, mid-event.
    if (!user) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    else if (user.role === 'athlete') router.replace('/training');
  }, [loading, user, router, pathname]);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      setEvents(await combineApi.listEvents());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load combines');
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    if (user) void load();
  }, [user, load]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!name || !eventDate) return;
    setCreating(true);
    try {
      const created = await combineApi.createEvent({
        event_name: name,
        event_date: eventDate,
        venue: venue.trim() || undefined,
      });
      router.push(`/combine/${created.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create the combine');
      setCreating(false);
    }
  }

  // Venues already used, so a returning event does not get a slightly different spelling
  const venueOptions = Array.from(
    new Set(events.map((e) => e.venue).filter(Boolean))
  ) as string[];

  if (loading || !user || user.role === 'athlete') return null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="section-title text-2xl">Combines</h1>
        <p className="mt-1 text-sm text-white/50">
          One-day testing events with live big-screen results.
        </p>
      </div>

      <form onSubmit={create} className="card flex flex-wrap items-end gap-3">
        <div className="min-w-[200px] flex-1">
          <label className="text-xs uppercase tracking-widest text-white/40">Event name</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Boxing Science Combine 2026"
            className="input mt-1 w-full"
            required
          />
        </div>
        <div className="min-w-[180px] flex-1">
          <label className="text-xs uppercase tracking-widest text-white/40">
            Location <span className="text-white/25">(optional)</span>
          </label>
          <input
            value={venue}
            onChange={(e) => setVenue(e.target.value)}
            placeholder="Boxing Science Performance Centre"
            list="combine-venue-options"
            className="input mt-1 w-full"
            autoComplete="off"
          />
          <datalist id="combine-venue-options">
            {venueOptions.map((option) => (
              <option key={option} value={option} />
            ))}
          </datalist>
        </div>
        <div>
          <label className="text-xs uppercase tracking-widest text-white/40">Date</label>
          <input
            type="date"
            value={eventDate}
            onChange={(e) => setEventDate(e.target.value)}
            className="input mt-1"
            required
          />
        </div>
        <button type="submit" disabled={creating} className="btn-primary disabled:opacity-40">
          {creating ? 'Creating…' : 'New combine'}
        </button>
      </form>

      {error && <p className="text-sm text-red-300">{error}</p>}

      {busy ? (
        <div className="flex justify-center py-10">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-accent border-t-transparent" />
        </div>
      ) : events.length === 0 ? (
        <p className="card text-center text-white/40">
          No combines yet. Create one above, import the roster, and open the big screen.
        </p>
      ) : (
        <ul className="space-y-2">
          {events.map((event) => (
            <li key={event.id}>
              <Link
                href={`/combine/${event.id}`}
                className="card flex flex-wrap items-center justify-between gap-3 transition-all hover:border-accent/50"
              >
                <div>
                  <p className="text-lg font-semibold text-white">{event.event_name}</p>
                  <p className="text-sm text-white/40">
                    {new Date(event.event_date).toLocaleDateString('en-GB', {
                      day: 'numeric',
                      month: 'short',
                      year: 'numeric',
                    })}
                    {event.venue ? ` · ${event.venue}` : ''}
                  </p>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-white/50">
                    {event.participant_count} boxers · {event.attempt_count} attempts
                  </span>
                  <span
                    className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-widest ${
                      STATUS_STYLES[event.status] ?? STATUS_STYLES.draft
                    }`}
                  >
                    {event.status}
                  </span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
