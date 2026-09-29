'use client';

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
  type ReactNode,
} from 'react';
import { authApi, type AuthResponse, onAuthError } from './api';

interface AuthUser {
  user_id: string;
  email: string;
  role: 'coach' | 'admin' | 'athlete';
  athlete_id?: string;
}

interface AuthContextType {
  user: AuthUser | null;
  loading: boolean;
  /** Session restore ran out of retries. `loading` is false by then, so pages can render it. */
  reconnecting: boolean;
  /** Start session restore again — for a "Retry" button on the reconnecting state. */
  retryAuth: () => void;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  signupAthlete: (email: string, password: string, inviteCode: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

/** Backoff for a failed /auth/me, capped at three retries (about one minute). */
const RESTORE_RETRY_DELAYS_MS = [10_000, 20_000, 30_000];

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [reconnecting, setReconnecting] = useState(false);
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmounted = useRef(false);

  // Restore session from HttpOnly cookie by calling /auth/me.
  // Only a 401 means "not signed in". A dropped frame on gym Wi-Fi or a backend
  // 5xx must not sign a station iPad out mid-event, so those retry; while they
  // do, `loading` stays true so the route guards hold instead of redirecting.
  const restoreSession = useCallback(() => {
    if (retryTimer.current) clearTimeout(retryTimer.current);
    setReconnecting(false);
    setLoading(true);

    const attempt = (attemptsMade: number) => {
      authApi
        .me()
        .then((data) => {
          if (unmounted.current) return;
          setUser({
            user_id: data.user_id,
            email: data.email || '',
            role: (data.role as 'coach' | 'admin' | 'athlete') || 'coach',
            athlete_id: data.athlete_id,
          });
          setReconnecting(false);
          setLoading(false);
        })
        .catch((err: unknown) => {
          if (unmounted.current) return;
          if ((err as { status?: number })?.status === 401) {
            setUser(null);
            setReconnecting(false);
            setLoading(false);
            return;
          }
          const delay = RESTORE_RETRY_DELAYS_MS[attemptsMade];
          if (delay === undefined) {
            // Out of retries. `loading` has to end here: while it is true every guarded
            // page renders null, so a station iPad would sit on a blank screen with no
            // way back in. The guards send it to /login?next=<station>, which renders
            // the reconnecting panel rather than the sign-in form — the cookie is still
            // valid, so nobody retypes the shared admin password, and `next` puts the
            // iPad back on its own station once a retry succeeds.
            setReconnecting(true);
            setLoading(false);
            return;
          }
          retryTimer.current = setTimeout(() => attempt(attemptsMade + 1), delay);
        });
    };

    attempt(0);
  }, []);

  useEffect(() => {
    unmounted.current = false;
    restoreSession();
    return () => {
      unmounted.current = true;
      if (retryTimer.current) clearTimeout(retryTimer.current);
    };
  }, [restoreSession]);

  // A station iPad is unattended for long stretches, so don't wait for someone to
  // press Retry: re-attempt when the network returns or when the tab comes back to
  // the front (Guided Access wakes it hours later).
  useEffect(() => {
    if (!reconnecting) return;
    const retryOnline = () => restoreSession();
    const retryVisible = () => {
      if (document.visibilityState === 'visible') restoreSession();
    };
    window.addEventListener('online', retryOnline);
    document.addEventListener('visibilitychange', retryVisible);
    return () => {
      window.removeEventListener('online', retryOnline);
      document.removeEventListener('visibilitychange', retryVisible);
    };
  }, [reconnecting, restoreSession]);

  // Listen for 401 errors from API layer to auto-logout
  useEffect(() => {
    const unsubscribe = onAuthError(() => {
      setUser(null);
    });
    return unsubscribe;
  }, []);

  const handleAuthResponse = useCallback((response: AuthResponse) => {
    const authUser: AuthUser = {
      user_id: response.user_id,
      email: response.email,
      role: 'coach', // Default on login/signup; will be refreshed on next me() call
    };
    setUser(authUser);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const response = await authApi.login(email, password);
      // Fetch actual role before setting user to avoid flash of wrong page
      try {
        const me = await authApi.me();
        setUser({
          user_id: response.user_id,
          email: response.email,
          role: (me.role as 'coach' | 'admin' | 'athlete') || 'coach',
          athlete_id: me.athlete_id,
        });
      } catch {
        handleAuthResponse(response);
      }
    },
    [handleAuthResponse]
  );

  const signup = useCallback(
    async (email: string, password: string) => {
      const response = await authApi.signup(email, password);
      // Fetch actual role before setting user to avoid flash of wrong page
      try {
        const me = await authApi.me();
        setUser({
          user_id: response.user_id,
          email: response.email,
          role: (me.role as 'coach' | 'admin' | 'athlete') || 'coach',
          athlete_id: me.athlete_id,
        });
      } catch {
        handleAuthResponse(response);
      }
    },
    [handleAuthResponse]
  );

  const signupAthlete = useCallback(
    async (email: string, password: string, inviteCode: string) => {
      const res = await fetch('/api/v1/auth/signup/athlete', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, invite_code: inviteCode }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Signup failed' }));
        throw new Error(err.detail || 'Signup failed');
      }
      const data = await res.json();
      // Fetch /me to get role and athlete_id
      try {
        const me = await authApi.me();
        setUser({
          user_id: me.user_id,
          email,
          role: (me.role as 'coach' | 'admin' | 'athlete') || 'athlete',
          athlete_id: me.athlete_id,
        });
      } catch {
        setUser({ user_id: data.user_id, email, role: 'athlete' });
      }
    },
    []
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // Ignore errors — clear local state regardless
    }
    try { localStorage.removeItem('bsams-selected-athlete'); } catch {}
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const me = await authApi.me();
      setUser({
        user_id: me.user_id,
        email: me.email || '',
        role: (me.role as 'coach' | 'admin' | 'athlete') || 'coach',
        athlete_id: me.athlete_id,
      });
    } catch {
      // Silently fail — user state unchanged
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        reconnecting,
        retryAuth: restoreSession,
        login,
        signup,
        signupAthlete,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
