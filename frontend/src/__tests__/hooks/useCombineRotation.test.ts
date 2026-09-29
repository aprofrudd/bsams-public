import { renderHook, act } from '@testing-library/react';
import { useCombineRotation } from '@/lib/hooks/useCombineRotation';

function setHidden(hidden: boolean) {
  Object.defineProperty(document, 'hidden', { configurable: true, value: hidden });
}

describe('useCombineRotation', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
    setHidden(false);
  });

  it('starts on the first panel and cycles back round', () => {
    const { result } = renderHook(() =>
      useCombineRotation(['summary', 'cmj', 'overall'], { intervalMs: 20_000 })
    );

    expect(result.current.active).toBe('summary');
    act(() => jest.advanceTimersByTime(20_000));
    expect(result.current.active).toBe('cmj');
    act(() => jest.advanceTimersByTime(40_000));
    expect(result.current.active).toBe('summary');
    expect(result.current.total).toBe(3);
  });

  it('holds still on a pinned panel', () => {
    const { result } = renderHook(() =>
      useCombineRotation(['summary', 'cmj'], { intervalMs: 20_000, pinned: 'cmj' })
    );

    expect(result.current.isPinned).toBe(true);
    expect(result.current.active).toBe('cmj');
    act(() => jest.advanceTimersByTime(120_000));
    expect(result.current.active).toBe('cmj');
  });

  it('keeps rotating when the pinned panel has no results yet', () => {
    // A second screen on ?panel=landmine before the landmine station has logged
    // anything: the panel is not in the available list, so the board must rotate
    // rather than freeze on a panel it cannot draw.
    const { result } = renderHook(() =>
      useCombineRotation(['summary', 'cmj'], { intervalMs: 20_000, pinned: 'landmine' })
    );

    expect(result.current.isPinned).toBe(false);
    expect(result.current.active).toBe('summary');
    // The footer dots read this index, so it must point at a real panel.
    expect(result.current.index).toBe(0);

    act(() => jest.advanceTimersByTime(20_000));
    expect(result.current.active).toBe('cmj');
    expect(result.current.index).toBe(1);
  });

  it('pauses while the tab is hidden', () => {
    const { result } = renderHook(() =>
      useCombineRotation(['summary', 'cmj'], { intervalMs: 20_000 })
    );

    setHidden(true);
    act(() => jest.advanceTimersByTime(60_000));
    expect(result.current.active).toBe('summary');
  });

  it('honours an explicit pause', () => {
    const { result } = renderHook(() =>
      useCombineRotation(['summary', 'cmj'], { intervalMs: 20_000, paused: true })
    );

    act(() => jest.advanceTimersByTime(60_000));
    expect(result.current.active).toBe('summary');
  });

  it('keeps the index in range when a panel disappears mid-event', () => {
    const { result, rerender } = renderHook(
      ({ panels }: { panels: string[] }) => useCombineRotation(panels, { intervalMs: 20_000 }),
      { initialProps: { panels: ['summary', 'cmj', 'overall'] } }
    );

    act(() => jest.advanceTimersByTime(40_000));
    expect(result.current.index).toBe(2);

    rerender({ panels: ['summary'] });
    expect(result.current.index).toBe(0);
    expect(result.current.active).toBe('summary');
  });

  it('reports no rotation for a single panel', () => {
    const { result } = renderHook(() => useCombineRotation(['summary'], { intervalMs: 20_000 }));

    act(() => jest.advanceTimersByTime(60_000));
    expect(result.current.active).toBe('summary');
    expect(result.current.total).toBe(1);
  });

  it('survives an empty panel list', () => {
    const { result } = renderHook(() => useCombineRotation([], { intervalMs: 20_000 }));

    expect(result.current.active).toBeNull();
    expect(result.current.total).toBe(0);
  });
});
