'use client';

import { useState, useEffect } from 'react';
import { adminApi } from '@/lib/api';
import type { AnonymisedAthlete, SharedEvent } from '@/lib/api';

export function SharedDataView() {
  const [athletes, setAthletes] = useState<AnonymisedAthlete[]>([]);
  const [selectedAthlete, setSelectedAthlete] = useState<AnonymisedAthlete | null>(null);
  const [events, setEvents] = useState<SharedEvent[]>([]);
  const [isLoadingAthletes, setIsLoadingAthletes] = useState(true);
  const [isLoadingEvents, setIsLoadingEvents] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAthletes();
  }, []);

  useEffect(() => {
    if (selectedAthlete) {
      loadEvents(selectedAthlete.id);
    } else {
      setEvents([]);
    }
  }, [selectedAthlete]);

  async function loadAthletes() {
    try {
      setIsLoadingAthletes(true);
      setError(null);
      const data = await adminApi.listSharedAthletes(0, 200);
      setAthletes(data);
    } catch {
      setError('Failed to load shared athletes');
    } finally {
      setIsLoadingAthletes(false);
    }
  }

  async function loadEvents(athleteId: string) {
    try {
      setIsLoadingEvents(true);
      const data = await adminApi.getSharedEvents(athleteId);
      setEvents(data);
    } catch {
      setEvents([]);
    } finally {
      setIsLoadingEvents(false);
    }
  }

  if (isLoadingAthletes) {
    return (
      <div className="text-center py-8">
        <div className="inline-block w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        <p className="mt-2 text-white/60">Loading shared data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-400">{error}</p>
        <button onClick={loadAthletes} className="btn-secondary mt-4">
          Retry
        </button>
      </div>
    );
  }

  if (athletes.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-white/60">No coaches have opted in to data sharing yet</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {/* Athlete list */}
      <div className="card md:col-span-1">
        <h3 className="section-title text-base mb-3">Shared Athletes</h3>
        <div className="space-y-2 max-h-[60vh] overflow-y-auto">
          {athletes.map((athlete) => (
            <button
              key={athlete.id}
              onClick={() => setSelectedAthlete(athlete)}
              className={`w-full text-left px-3 py-2.5 min-h-[44px] rounded-lg transition-colors ${
                selectedAthlete?.id === athlete.id
                  ? 'bg-accent text-primary'
                  : 'hover:bg-secondary-muted active:bg-secondary-muted/80'
              }`}
            >
              <div className="font-medium">{athlete.anonymous_name}</div>
              <div className="text-xs opacity-70 capitalize">{athlete.gender}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Events table */}
      <div className="card md:col-span-2">
        {selectedAthlete ? (
          <>
            <h3 className="section-title text-base mb-3">
              {selectedAthlete.anonymous_name} — Events
            </h3>

            {isLoadingEvents ? (
              <div className="text-center py-8">
                <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
              </div>
            ) : events.length === 0 ? (
              <p className="text-white/60 text-center py-8">No events found</p>
            ) : (
              <>
              {/* Mobile card list */}
              <div className="sm:hidden space-y-2">
                {events.map((event) => (
                  <div key={event.id} className="bg-[#07083D] border border-[#2D5585] rounded-lg mb-2 p-3">
                    <div className="text-white text-sm font-medium">
                      {formatDate(event.event_date)}
                    </div>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {Object.entries(event.metrics)
                        .filter(([key]) => key !== 'test_type' && key !== 'body_mass_kg')
                        .map(([key, value]) => (
                          <span
                            key={key}
                            className="px-2 py-0.5 rounded bg-white/5 text-white/80 text-xs"
                          >
                            {key}: {typeof value === 'number' ? value.toFixed(2) : value}
                          </span>
                        ))}
                    </div>
                  </div>
                ))}
              </div>

              {/* Desktop table */}
              <div className="hidden sm:block overflow-x-auto">
                <table className="w-full min-w-[400px]">
                  <thead>
                    <tr className="border-b border-secondary-muted">
                      <th className="text-left py-2 px-3 text-white/60 font-medium text-sm">Date</th>
                      <th className="text-left py-2 px-3 text-white/60 font-medium text-sm">Metrics</th>
                    </tr>
                  </thead>
                  <tbody>
                    {events.map((event) => (
                      <tr key={event.id} className="border-b border-secondary-muted/50">
                        <td className="py-2 px-3 text-sm whitespace-nowrap">
                          {formatDate(event.event_date)}
                        </td>
                        <td className="py-2 px-3 text-sm">
                          <div className="flex flex-wrap gap-2">
                            {Object.entries(event.metrics)
                              .filter(([key]) => key !== 'test_type' && key !== 'body_mass_kg')
                              .map(([key, value]) => (
                                <span
                                  key={key}
                                  className="px-2 py-0.5 rounded bg-white/5 text-white/80 text-xs"
                                >
                                  {key}: {typeof value === 'number' ? value.toFixed(2) : value}
                                </span>
                              ))}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              </>
            )}
          </>
        ) : (
          <p className="text-white/60 text-center py-8">Select an athlete to view their events</p>
        )}
      </div>
    </div>
  );
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}
