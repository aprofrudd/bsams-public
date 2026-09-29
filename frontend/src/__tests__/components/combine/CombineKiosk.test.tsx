import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CombineKiosk } from '@/components/combine/CombineKiosk';
import type { CombineLeaderboard } from '@/lib/types';

let searchParams = new URLSearchParams();
jest.mock('next/navigation', () => ({
  useSearchParams: () => searchParams,
}));

jest.mock('@/lib/hooks/useWakeLock', () => ({
  useWakeLock: () => ({ acquire: jest.fn(), release: jest.fn() }),
}));

const board: CombineLeaderboard = {
  event_name: 'Rehearsal Combine',
  event_date: '2026-09-19',
  venue: 'Performance Centre',
  results_updated_at: '2026-09-19T09:00:00Z',
  participant_count: 12,
  filters: {},
  unsynced_count: 0,
  stations: [
    { station: 'cmj', completed: 12 },
    { station: 'pogo', completed: 12 },
  ] as CombineLeaderboard['stations'],
  overall: [],
  score_basis: 'z',
};

jest.mock('@/lib/hooks/useCombinePolling', () => ({
  useCombinePolling: () => ({
    data: board,
    error: null,
    loading: false,
    staleSeconds: 0,
    lastUpdated: new Date('2026-09-19T09:00:00Z'),
    refresh: jest.fn(),
  }),
}));

// The panels themselves are covered by their own suites; here they only need to
// say which one is on screen.
jest.mock('@/components/combine/SummaryPanel', () => ({
  SummaryPanel: () => <div>panel:summary</div>,
}));
jest.mock('@/components/combine/StationPanel', () => ({
  StationPanel: ({ panel }: { panel: { station: string } }) => <div>{`panel:${panel.station}`}</div>,
}));
jest.mock('@/components/combine/OverallPanel', () => ({
  OverallPanel: () => <div>panel:overall</div>,
}));

describe('CombineKiosk pin control', () => {
  beforeEach(() => {
    searchParams = new URLSearchParams();
    window.history.replaceState(null, '', '/combine/live/tok');
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  const advance = (ms: number) => act(() => { jest.advanceTimersByTime(ms); });

  it('rotates until a panel is pinned, then holds it and keeps the URL in step', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    render(<CombineKiosk token="tok" />);

    expect(screen.getByText('panel:summary')).toBeInTheDocument();
    advance(20_000);
    expect(screen.getByText('panel:cmj')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Pin CMJ' }));

    advance(120_000);
    expect(screen.getByText('panel:cmj')).toBeInTheDocument();
    expect(window.location.search).toContain('panel=cmj');
  });

  it('resumes rotating when the pin is released, and drops the parameter', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    searchParams = new URLSearchParams('panel=cmj');
    window.history.replaceState(null, '', '/combine/live/tok?panel=cmj');
    render(<CombineKiosk token="tok" />);

    expect(screen.getByText('panel:cmj')).toBeInTheDocument();
    advance(60_000);
    expect(screen.getByText('panel:cmj')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /resume/i }));
    expect(window.location.search).not.toContain('panel=');
    // Releasing the pin leaves the panel on screen and carries on from there.
    expect(screen.getByText('panel:cmj')).toBeInTheDocument();

    advance(20_000);
    expect(screen.getByText('panel:pogo')).toBeInTheDocument();
  });

  it('pins straight from a dot without waiting for the panel to come round', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    render(<CombineKiosk token="tok" />);

    await user.click(screen.getByRole('button', { name: 'Pin the Pogo panel' }));
    expect(screen.getByText('panel:pogo')).toBeInTheDocument();
    advance(120_000);
    expect(screen.getByText('panel:pogo')).toBeInTheDocument();
  });
});
