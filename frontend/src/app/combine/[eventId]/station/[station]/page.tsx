'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { combineApi } from '@/lib/api';
import type { CombineEvent, CombineStation } from '@/lib/types';
import { STATION_DEFINITIONS } from '@/components/combine/stations/stationFields';
import { StationEntryScreen } from '@/components/combine/stations/StationEntryScreen';

const STATIONS = Object.keys(STATION_DEFINITIONS) as CombineStation[];

export default function CombineStationPage({
  params,
}: {
  params: { eventId: string; station: string };
}) {
  const { eventId, station } = params;
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const [event, setEvent] = useState<CombineEvent | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (loading) return;
    // Back to this station after signing in. Without it a session that lapses
    // mid-event drops the operator on /training with a queue in front of them.
    if (!user) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    else if (user.role === 'athlete') router.replace('/training');
  }, [loading, user, router, pathname]);

  useEffect(() => {
    if (!user) return;
    combineApi
      .getEvent(eventId)
      .then(setEvent)
      .catch((err) => setError(err instanceof Error ? err.message : 'Event not found'));
  }, [user, eventId]);

  if (loading || !user || user.role === 'athlete') return null;

  if (!STATIONS.includes(station as CombineStation)) {
    return <p className="text-white/60">Unknown station.</p>;
  }
  const stationKey = station as CombineStation;
  const definition = STATION_DEFINITIONS[stationKey];

  if (error) {
    return (
      <div className="card">
        <p className="text-red-300">{error}</p>
        <Link href="/combine" className="mt-3 inline-block text-accent">
          Back to combines
        </Link>
      </div>
    );
  }

  if (!event) {
    return (
      <div className="flex justify-center py-16">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-accent border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link
            href={`/combine/${eventId}`}
            className="text-xs uppercase tracking-widest text-white/40 hover:text-white/70"
          >
            ← {event.event_name}
          </Link>
          <h1 className="section-title text-2xl">{definition.label}</h1>
        </div>

        <nav className="scroll-container flex flex-nowrap gap-1">
          {STATIONS.map((key) => (
            <Link
              key={key}
              href={`/combine/${eventId}/station/${key}`}
              className={`min-h-[44px] whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition-all ${
                key === stationKey
                  ? 'bg-accent text-[#090A3D]'
                  : 'bg-secondary-muted/20 text-white/60 hover:bg-secondary-muted/40'
              }`}
            >
              {STATION_DEFINITIONS[key].shortLabel}
            </Link>
          ))}
        </nav>
      </div>

      <StationEntryScreen event={event} station={stationKey} />
    </div>
  );
}
