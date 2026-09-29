import { useRef, useCallback, useEffect } from 'react';

/**
 * Keeps the screen awake while something is running.
 *
 * Browsers drop the wake-lock sentinel whenever the tab is backgrounded — even
 * briefly — and never restore it. For a timer that is a nuisance; for a board left
 * on a gym TV all day it means the screen goes dark and stays dark. So the lock is
 * re-acquired on visibilitychange, and always released on unmount.
 */
export function useWakeLock() {
  const wakeLockRef = useRef<WakeLockSentinel | null>(null);
  const wantedRef = useRef(false);

  const acquire = useCallback(async () => {
    wantedRef.current = true;
    if ('wakeLock' in navigator) {
      try {
        wakeLockRef.current = await navigator.wakeLock.request('screen');
      } catch {
        // Silent fallback — wake lock not available
      }
    }
  }, []);

  const release = useCallback(() => {
    wantedRef.current = false;
    if (wakeLockRef.current) {
      wakeLockRef.current.release().catch(() => {});
      wakeLockRef.current = null;
    }
  }, []);

  useEffect(() => {
    const handleVisibility = () => {
      if (!wantedRef.current || document.hidden) return;
      if (wakeLockRef.current && !wakeLockRef.current.released) return;
      void acquire();
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibility);
      // Release on unmount so a lock can never outlive the component that took it.
      if (wakeLockRef.current) {
        wakeLockRef.current.release().catch(() => {});
        wakeLockRef.current = null;
      }
      wantedRef.current = false;
    };
  }, [acquire]);

  return { acquire, release };
}
