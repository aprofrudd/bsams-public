'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Polls a JSON endpoint and keeps the last good payload on screen.
 *
 * There is no realtime transport in BSAMS — no WebSocket, no SSE, and the backend
 * CSP has no `wss:` — so the gym board polls. Two rules matter more than the
 * cadence:
 *
 *   1. Never blank the screen on error. A dropped request shows the previous
 *      board, not an empty one.
 *   2. Make staleness visible. A frozen board that still looks live is the worst
 *      failure mode on a testing day, so `staleSeconds` drives a visible state.
 *
 * Uses If-None-Match, so an unchanged board costs a ~200 byte 304 rather than the
 * full payload.
 */

const BACKOFF_MS = [10_000, 20_000, 30_000];
const REQUEST_TIMEOUT_MS = 10_000;
/**
 * How many 404s in a row mean the board is really gone.
 *
 * Turn off, revoke, rotate and expiry all answer 404. One can be a blip, but three
 * in a row has to clear the screen: leaving minors' names on a TV in a public hall
 * after the coach pressed Turn off is the failure this counter exists to prevent.
 */
const CONSECUTIVE_404_LIMIT = 3;

export interface CombinePollingState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  /** Seconds since the last successful fetch. */
  staleSeconds: number;
  lastUpdated: Date | null;
  refresh: () => void;
}

export function useCombinePolling<T>(
  url: string | null,
  intervalMs = 5000
): CombinePollingState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [staleSeconds, setStaleSeconds] = useState(0);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const etagRef = useRef<string | null>(null);
  const failuresRef = useRef(0);
  const notFoundRef = useRef(0);
  const lastSuccessRef = useRef<number | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const mountedRef = useRef(true);

  const fetchOnce = useCallback(async () => {
    if (!url) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    let timedOut = false;
    // Set in the 404 branch below, which then throws into the same catch. The catch
    // has no status to read, so this is how it tells a revoked link from a dropped
    // connection.
    let saw404 = false;
    const timeout = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, REQUEST_TIMEOUT_MS);

    try {
      const headers: HeadersInit = {};
      if (etagRef.current) headers['If-None-Match'] = etagRef.current;

      const response = await fetch(url, { headers, signal: controller.signal });

      if (response.status === 304) {
        failuresRef.current = 0;
        notFoundRef.current = 0;
        lastSuccessRef.current = Date.now();
        if (mountedRef.current) {
          setError(null);
          setLoading(false);
        }
        return;
      }

      if (!response.ok) {
        if (response.status === 404) {
          saw404 = true;
          notFoundRef.current += 1;
          if (notFoundRef.current >= CONSECUTIVE_404_LIMIT) {
            // Drop the ETag too, or a restored link would answer 304 to a
            // conditional request and the board would never fill back in.
            etagRef.current = null;
            if (mountedRef.current) {
              setData(null);
              setLastUpdated(null);
            }
          }
        }
        // A 429 is transient here, not fatal — back off and try again.
        throw new Error(
          response.status === 404
            ? 'This board is not available. The link may have expired.'
            : `Request failed (${response.status})`
        );
      }

      const etag = response.headers.get('etag');
      if (etag) etagRef.current = etag;

      const payload = (await response.json()) as T;
      failuresRef.current = 0;
      notFoundRef.current = 0;
      lastSuccessRef.current = Date.now();
      if (mountedRef.current) {
        setData(payload);
        setError(null);
        setLoading(false);
        setLastUpdated(new Date());
      }
    } catch (err) {
      // An abort we did not time out ourselves means a newer request replaced this
      // one — a refresh, a filter change, or unmount. That is not a failure, and
      // counting it would back the board off for a request nobody was waiting on.
      if (controller.signal.aborted && !timedOut) return;
      // Only genuinely consecutive 404s clear the screen. A dropped connection between
      // two of them never showed the link to be gone, so the count starts again — the
      // backend answers a failed lookup with 503 precisely so this stays distinguishable.
      if (!saw404) notFoundRef.current = 0;
      failuresRef.current += 1;
      if (mountedRef.current) {
        // Deliberately keep `data` — the last good board stays on screen.
        setError(err instanceof Error ? err.message : 'Connection lost');
        setLoading(false);
      }
    } finally {
      clearTimeout(timeout);
    }
  }, [url]);

  const schedule = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    const failures = failuresRef.current;
    const delay =
      failures === 0
        ? intervalMs
        : BACKOFF_MS[Math.min(failures - 1, BACKOFF_MS.length - 1)];
    timerRef.current = setTimeout(async () => {
      if (typeof document !== 'undefined' && document.hidden) {
        schedule();
        return;
      }
      await fetchOnce();
      schedule();
    }, delay);
  }, [fetchOnce, intervalMs]);

  const refresh = useCallback(() => {
    failuresRef.current = 0;
    void fetchOnce().then(() => schedule());
  }, [fetchOnce, schedule]);

  useEffect(() => {
    mountedRef.current = true;
    if (!url) {
      setLoading(false);
      return;
    }
    void fetchOnce().then(() => schedule());

    const onVisible = () => {
      if (!document.hidden) refresh();
    };
    const onOnline = () => refresh();
    document.addEventListener('visibilitychange', onVisible);
    window.addEventListener('online', onOnline);

    return () => {
      mountedRef.current = false;
      if (timerRef.current) clearTimeout(timerRef.current);
      abortRef.current?.abort();
      document.removeEventListener('visibilitychange', onVisible);
      window.removeEventListener('online', onOnline);
    };
    // refresh/schedule are stable for a given url
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url]);

  // Tick the staleness clock so the UI can show "reconnecting" without a re-fetch.
  //
  // Frozen while the tab is hidden: polling is deliberately paused there, so letting
  // the clock run would show RECONNECTING for a board that is simply in the
  // background — crying wolf, and training people to ignore the one indicator that
  // matters when the wifi really does drop.
  useEffect(() => {
    const id = setInterval(() => {
      if (lastSuccessRef.current == null) return;
      if (typeof document !== 'undefined' && document.hidden) return;
      setStaleSeconds(Math.floor((Date.now() - lastSuccessRef.current) / 1000));
    }, 1000);
    return () => clearInterval(id);
  }, []);

  return { data, error, loading, staleSeconds, lastUpdated, refresh };
}
