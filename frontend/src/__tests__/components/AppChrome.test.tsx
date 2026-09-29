import { render, screen } from '@testing-library/react';
import { AppChrome } from '@/components/AppChrome';

const mockPathname = jest.fn<string, []>();

jest.mock('next/navigation', () => ({
  usePathname: () => mockPathname(),
  useRouter: () => ({ push: jest.fn(), replace: jest.fn() }),
}));

jest.mock('@/components/AppHeader', () => ({
  AppHeader: () => <header data-testid="app-header" />,
}));
jest.mock('@/components/OnboardingGate', () => ({
  OnboardingGate: () => null,
}));
jest.mock('@/components/ConsentGate', () => ({
  ConsentGate: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
jest.mock('@/components/CookieBanner', () => ({
  CookieBanner: () => <div data-testid="cookie-banner" />,
}));

describe('AppChrome', () => {
  it('renders the app chrome on a normal route', () => {
    mockPathname.mockReturnValue('/training');
    render(
      <AppChrome>
        <p>content</p>
      </AppChrome>
    );
    expect(screen.getByTestId('app-header')).toBeInTheDocument();
    expect(screen.getByTestId('cookie-banner')).toBeInTheDocument();
    expect(screen.getByText('Privacy Policy')).toBeInTheDocument();
  });

  it('renders the kiosk bare, so the board fills a gym TV', () => {
    mockPathname.mockReturnValue('/combine/live/abc123');
    render(
      <AppChrome>
        <p>board</p>
      </AppChrome>
    );
    expect(screen.queryByTestId('app-header')).not.toBeInTheDocument();
    expect(screen.queryByTestId('cookie-banner')).not.toBeInTheDocument();
    expect(screen.getByText('board')).toBeInTheDocument();
  });

  it('keeps the chrome on the combine console, which is a normal page', () => {
    mockPathname.mockReturnValue('/combine/abc123');
    render(
      <AppChrome>
        <p>console</p>
      </AppChrome>
    );
    expect(screen.getByTestId('app-header')).toBeInTheDocument();
  });
});
