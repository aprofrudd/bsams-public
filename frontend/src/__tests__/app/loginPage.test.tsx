import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LoginPage from '@/app/login/page';
import { safeNextPath } from '@/lib/safeNextPath';

const mockReplace = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({ replace: mockReplace, push: jest.fn() }),
}));

const mockLogin = jest.fn();
const mockRetryAuth = jest.fn();
const mockAuthState: {
  user: { user_id: string } | null;
  loading: boolean;
  reconnecting: boolean;
} = { user: null, loading: false, reconnecting: false };

jest.mock('@/lib/auth', () => ({
  useAuth: () => ({
    ...mockAuthState,
    retryAuth: mockRetryAuth,
    login: mockLogin,
    signup: jest.fn(),
  }),
}));

jest.mock('@/lib/api', () => ({
  authApi: { forgotPassword: jest.fn() },
  fetchApi: jest.fn(),
}));

function visitLogin(search: string) {
  window.history.replaceState({}, '', `/login${search}`);
}

async function signIn() {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText('Email'), 'admin@example.com');
  await user.type(screen.getByLabelText('Password'), 'Password1');
  await user.click(screen.getByRole('button', { name: 'Log In' }));
}

describe('safeNextPath', () => {
  // Six iPads sign into one admin account, so an open redirect off /login lands on
  // a lookalike page that harvests the password owning every event and every minor's record.
  it.each([
    ['a plain in-app path', '?next=/combine/e1/station/cmj', '/combine/e1/station/cmj'],
    ['a path with query and hash', '?next=/combine/e1%3Ftab%3Droster%23top', '/combine/e1?tab=roster#top'],
    ['a protocol-relative URL', '?next=//evil.example', null],
    ['a backslash-escaped URL', '?next=/%5Cevil.example', null],
    ['an absolute URL', '?next=https://evil.example', null],
    // URLSearchParams decodes these, and the URL parser then strips the control
    // character before resolving — so a prefix check on the raw string is defeated.
    ['a tab', '?next=/%09//evil.example', null],
    ['a newline', '?next=/%0a//evil.example', null],
    ['a carriage return', '?next=/%0d//evil.example', null],
    // new URL() throws on this one; a throw in a render-time initialiser white-screens /login.
    ['an unparseable URL', '?next=//evil:999999/', null],
    ['a javascript: URL', '?next=javascript:alert(1)', null],
    ['no next at all', '', null],
    ['an empty next', '?next=', null],
  ])('%s', (_label, search, expected) => {
    expect(safeNextPath(search)).toBe(expected);
  });
});

describe('LoginPage', () => {
  beforeEach(() => {
    mockReplace.mockReset();
    mockLogin.mockReset().mockResolvedValue(undefined);
    mockRetryAuth.mockReset();
    mockAuthState.user = null;
    mockAuthState.loading = false;
    mockAuthState.reconnecting = false;
  });

  it('returns the operator to their station after signing in', async () => {
    visitLogin('?next=/combine/e1/station/cmj');
    render(<LoginPage />);

    await signIn();

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/combine/e1/station/cmj'));
  });

  it('ignores an off-site next and goes home instead', async () => {
    visitLogin('?next=/%09//evil.example');
    render(<LoginPage />);

    await signIn();

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/'));
  });

  it('offers a retry instead of the sign-in form while the session is reconnecting', async () => {
    // The cookie is still valid — the backend is not answering. Asking for the shared
    // admin password here is both useless and the thing an attacker wants.
    mockAuthState.reconnecting = true;
    visitLogin('');
    render(<LoginPage />);

    expect(screen.queryByLabelText('Password')).not.toBeInTheDocument();

    await userEvent.setup().click(screen.getByRole('button', { name: /try again/i }));

    expect(mockRetryAuth).toHaveBeenCalled();
  });
});
