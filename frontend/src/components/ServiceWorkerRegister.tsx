'use client';

import { useEffect } from 'react';

/**
 * Registers the offline service worker — in production only.
 *
 * `sw.js` serves `/_next/static/` stale-while-revalidate, which is right for a gym
 * with patchy wifi and wrong for development: Next reuses chunk URLs across
 * recompiles, so an installed worker keeps serving the previous build's JavaScript
 * and code changes silently never appear.
 *
 * In development it also unregisters anything already installed, so a developer who
 * picked one up from a production visit (or an earlier build) is not stuck with it.
 */
export function ServiceWorkerRegister() {
  useEffect(() => {
    if (!('serviceWorker' in navigator)) return;

    if (process.env.NODE_ENV !== 'production') {
      navigator.serviceWorker
        .getRegistrations()
        .then((registrations) => {
          registrations.forEach((registration) => void registration.unregister());
        })
        .catch(() => {
          // Nothing registered, or the browser refused — nothing to clean up.
        });
      return;
    }

    navigator.serviceWorker.register('/sw.js').catch(() => {
      // SW registration failed — silently ignore (e.g. localhost HTTP)
    });
  }, []);

  return null;
}
