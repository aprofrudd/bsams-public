import { useState, useEffect } from 'react';

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const mql = window.matchMedia(query);
    setMatches(mql.matches);
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches);
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }, [query]);

  return matches;
}

/** True when viewport is below Tailwind sm (640px) */
export function useIsMobile() {
  return !useMediaQuery('(min-width: 640px)');
}

/** True when viewport is below Tailwind md (768px) — used for bottom sheet modal threshold */
export function useIsMobileModal() {
  return !useMediaQuery('(min-width: 768px)');
}

/** True when viewport is at least Tailwind lg (1024px) */
export function useIsDesktop() {
  return useMediaQuery('(min-width: 1024px)');
}
