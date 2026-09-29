'use client';

import { useState, useEffect, useCallback } from 'react';
import { trainingTypesApi } from '@/lib/api';
import type { TrainingTypeItem } from '@/lib/api';

/**
 * Hook to load dynamic training types (system defaults + coach custom).
 * Falls back to hardcoded defaults if the API call fails.
 */
export function useTrainingTypes() {
  const [types, setTypes] = useState<string[]>(['Strength', 'Mobility', 'Conditioning']);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    try {
      const items = await trainingTypesApi.list();
      setTypes(items.map((t: TrainingTypeItem) => t.type_name));
    } catch {
      // Fallback to defaults on error
      setTypes(['Strength', 'Mobility', 'Conditioning']);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const addType = useCallback(async (name: string): Promise<boolean> => {
    try {
      await trainingTypesApi.create(name);
      await reload();
      return true;
    } catch {
      return false;
    }
  }, [reload]);

  return { types, loading, reload, addType };
}
