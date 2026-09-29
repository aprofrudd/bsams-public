'use client';

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { useAuth } from '../auth';
import { athletesApi } from '../api';
import type { Athlete } from '@/lib/types';

interface AthleteContextType {
  selectedAthlete: Athlete | null;
  setSelectedAthlete: (athlete: Athlete | null) => void;
  athleteVersion: number;
  bumpAthleteVersion: () => void;
  athleteError: string | null;
}

const AthleteContext = createContext<AthleteContextType | null>(null);

const STORAGE_KEY = 'bsams-selected-athlete';

export function AthleteProvider({ children }: { children: ReactNode }) {
  const [selectedAthlete, setSelectedAthlete] = useState<Athlete | null>(null);
  const [athleteVersion, setAthleteVersion] = useState(0);
  const [athleteError, setAthleteError] = useState<string | null>(null);
  const { user } = useAuth();

  const handleSetSelectedAthlete = useCallback((athlete: Athlete | null) => {
    setSelectedAthlete(athlete);
    try {
      if (athlete) localStorage.setItem(STORAGE_KEY, athlete.id);
      else localStorage.removeItem(STORAGE_KEY);
    } catch { /* ignore */ }
  }, []);

  const bumpAthleteVersion = useCallback(() => {
    setAthleteVersion(v => v + 1);
  }, []);

  // Auto-load athlete record for athlete role
  useEffect(() => {
    if (user?.role === 'athlete' && user.athlete_id) {
      setAthleteError(null);
      athletesApi.get(user.athlete_id)
        .then((data) => handleSetSelectedAthlete(data))
        .catch((err) => {
          console.error('Failed to load athlete record:', err);
          // Fallback: try list endpoint (returns own record for athlete role)
          athletesApi.list()
            .then((list) => {
              if (list.length > 0) {
                handleSetSelectedAthlete(list[0]);
              } else {
                setAthleteError('Your account hasn\'t been linked to an athlete profile yet. Please contact your coach.');
              }
            })
            .catch(() => {
              setAthleteError('Your account hasn\'t been linked to an athlete profile yet. Please contact your coach.');
            });
        });
    } else if (user?.role === 'athlete' && !user.athlete_id) {
      setAthleteError(null);
      // athlete_id not in /me response — try list endpoint
      athletesApi.list()
        .then((list) => {
          if (list.length > 0) {
            handleSetSelectedAthlete(list[0]);
          } else {
            setAthleteError('Your account hasn\'t been linked to an athlete profile yet. Please contact your coach.');
          }
        })
        .catch(() => {
          setAthleteError('Your account hasn\'t been linked to an athlete profile yet. Please contact your coach.');
        });
    }
  }, [user?.role, user?.athlete_id, handleSetSelectedAthlete]);

  return (
    <AthleteContext.Provider value={{ selectedAthlete, setSelectedAthlete: handleSetSelectedAthlete, athleteVersion, bumpAthleteVersion, athleteError }}>
      {children}
    </AthleteContext.Provider>
  );
}

export function useAthleteContext() {
  const context = useContext(AthleteContext);
  if (!context) {
    throw new Error('useAthleteContext must be used within an AthleteProvider');
  }
  return context;
}
