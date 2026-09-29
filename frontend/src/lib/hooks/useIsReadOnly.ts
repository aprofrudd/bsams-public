'use client';

import { useAuth } from '../auth';

export function useIsReadOnly(): boolean {
  const { user } = useAuth();
  return user?.role === 'athlete';
}
