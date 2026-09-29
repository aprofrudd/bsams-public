import { useState, useEffect, useMemo, useCallback } from 'react';
import { athletesApi } from '@/lib/api';
import type { Athlete } from '@/lib/types';

interface UseAthleteSelectionReturn {
  athletes: Athlete[];
  loading: boolean;
  selectedIds: Set<string>;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  filteredAthletes: Athlete[];
  toggleAthlete: (id: string) => void;
  toggleAll: () => void;
  error: string | null;
}

const getAthleteName = (a: Athlete): string => {
  if (a.first_name && a.surname) return `${a.first_name} ${a.surname}`;
  return a.name;
};

export const useAthleteSelection = (): UseAthleteSelectionReturn => {
  const [athletes, setAthletes] = useState<Athlete[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await athletesApi.list();
        setAthletes(data);
      } catch {
        setError('Failed to load athletes');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const filteredAthletes = useMemo(() => {
    if (!searchQuery.trim()) return athletes;
    const q = searchQuery.toLowerCase();
    return athletes.filter((a) => getAthleteName(a).toLowerCase().includes(q));
  }, [athletes, searchQuery]);

  const toggleAthlete = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleAll = useCallback(() => {
    setSelectedIds((prev) => {
      const allSelected = filteredAthletes.length > 0 && filteredAthletes.every((a) => prev.has(a.id));
      if (allSelected) {
        const next = new Set(prev);
        filteredAthletes.forEach((a) => next.delete(a.id));
        return next;
      } else {
        const next = new Set(prev);
        filteredAthletes.forEach((a) => next.add(a.id));
        return next;
      }
    });
  }, [filteredAthletes]);

  return {
    athletes,
    loading,
    selectedIds,
    searchQuery,
    setSearchQuery,
    filteredAthletes,
    toggleAthlete,
    toggleAll,
    error,
  };
};

export { getAthleteName };
