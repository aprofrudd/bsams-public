import { act, render, screen } from '@testing-library/react';
import { AuthProvider, useAuth } from '@/lib/auth';
import { authApi } from '@/lib/api';

jest.mock('@/lib/api', () => ({
  authApi: { me: jest.fn() },
  onAuthError: jest.fn(() => () => {}),
}));

const me = authApi.me as jest.Mock;

/** Mirrors the ApiError thrown by fetchApi: a status plus a message. */
class FakeApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

function Probe() {
  const { user, loading, reconnecting } = useAuth();
  return (
    <>
      <p>{reconnecting ? 'reconnecting' : loading ? 'loading' : user ? `user:${user.user_id}` : 'signed-out'}</p>
      <p data-testid="loading">{String(loading)}</p>
    </>
  );
}

function renderProvider() {
  render(
    <AuthProvider>
      <Probe />
    </AuthProvider>
  );
}

/** Let the pending /auth/me promise settle inside act(). */
async function settle() {
  await act(async () => {});
}

/** Advance to the next scheduled retry and let it settle. */
async function advance(ms: number) {
  await act(async () => {
    jest.advanceTimersByTime(ms);
  });
}

/** Burn the whole retry ladder (initial attempt plus the three backoffs). */
async function exhaustRetries() {
  renderProvider();
  await settle();
  await advance(10_000);
  await advance(20_000);
  await advance(30_000);
}

describe('AuthProvider session restore', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    me.mockReset();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('signs the user out only when /auth/me says 401', async () => {
    me.mockRejectedValue(new FakeApiError(401, 'Not authenticated'));

    renderProvider();
    await settle();

    expect(screen.getByText('signed-out')).toBeInTheDocument();
    expect(me).toHaveBeenCalledTimes(1);
  });

  it('retries a network blip instead of dropping the session', async () => {
    me.mockRejectedValueOnce(new TypeError('Failed to fetch')).mockResolvedValueOnce({
      user_id: 'u1',
      role: 'admin',
      email: 'admin@example.com',
    });

    renderProvider();
    await settle();

    // Still loading, never signed out — a station iPad must not bounce to /login.
    expect(screen.queryByText('signed-out')).not.toBeInTheDocument();

    await advance(10_000);

    expect(screen.getByText('user:u1')).toBeInTheDocument();
  });

  it('surfaces a reconnecting state after three failed retries', async () => {
    me.mockRejectedValue(new FakeApiError(503, 'Service unavailable'));

    await exhaustRetries();

    expect(screen.getByText('reconnecting')).toBeInTheDocument();
    expect(screen.queryByText('signed-out')).not.toBeInTheDocument();
    expect(me).toHaveBeenCalledTimes(4);

    // Capped at three retries — no fourth attempt keeps firing at the API.
    await advance(60_000);
    expect(me).toHaveBeenCalledTimes(4);
  });

  it('stops loading once the retries are exhausted, so pages can render something', async () => {
    // While `loading` is true every guarded page renders null and /login renders
    // "Loading...", so a station iPad sits on a blank screen with no way back in.
    me.mockRejectedValue(new FakeApiError(503, 'Service unavailable'));

    await exhaustRetries();

    expect(screen.getByTestId('loading')).toHaveTextContent('false');
  });

  it('retries by itself when the iPad comes back online', async () => {
    me.mockRejectedValue(new FakeApiError(503, 'Service unavailable'));

    await exhaustRetries();

    me.mockReset();
    me.mockResolvedValue({ user_id: 'u1', role: 'admin', email: 'admin@example.com' });

    await act(async () => {
      window.dispatchEvent(new Event('online'));
    });

    expect(screen.getByText('user:u1')).toBeInTheDocument();
  });

  it('retries when a backgrounded tab is brought back to the front', async () => {
    // Guided Access wakes the station tab hours later; nobody is watching the screen
    // to press Retry.
    me.mockRejectedValue(new FakeApiError(503, 'Service unavailable'));

    await exhaustRetries();

    me.mockReset();
    me.mockResolvedValue({ user_id: 'u1', role: 'admin', email: 'admin@example.com' });

    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'));
    });

    expect(screen.getByText('user:u1')).toBeInTheDocument();
  });
});
