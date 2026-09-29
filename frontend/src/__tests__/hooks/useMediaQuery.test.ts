import { renderHook, act } from '@testing-library/react';
import { useMediaQuery } from '@/lib/hooks/useMediaQuery';

function createMockMatchMedia(matches: boolean) {
  const listeners: Array<(e: MediaQueryListEvent) => void> = [];
  const mql = {
    matches,
    media: '',
    onchange: null,
    addEventListener: jest.fn((_event: string, handler: (e: MediaQueryListEvent) => void) => {
      listeners.push(handler);
    }),
    removeEventListener: jest.fn((_event: string, handler: (e: MediaQueryListEvent) => void) => {
      const idx = listeners.indexOf(handler);
      if (idx !== -1) listeners.splice(idx, 1);
    }),
    addListener: jest.fn(),
    removeListener: jest.fn(),
    dispatchEvent: jest.fn(),
  };

  const trigger = (newMatches: boolean) => {
    mql.matches = newMatches;
    listeners.forEach((fn) => fn({ matches: newMatches } as MediaQueryListEvent));
  };

  return { mql, trigger };
}

describe('useMediaQuery', () => {
  const originalMatchMedia = window.matchMedia;

  afterEach(() => {
    window.matchMedia = originalMatchMedia;
  });

  it('returns false when query does not match', () => {
    const { mql } = createMockMatchMedia(false);
    window.matchMedia = jest.fn().mockReturnValue(mql);

    const { result } = renderHook(() => useMediaQuery('(min-width: 640px)'));
    expect(result.current).toBe(false);
  });

  it('returns true when query matches', () => {
    const { mql } = createMockMatchMedia(true);
    window.matchMedia = jest.fn().mockReturnValue(mql);

    const { result } = renderHook(() => useMediaQuery('(min-width: 640px)'));
    expect(result.current).toBe(true);
  });

  it('updates on change event', () => {
    const { mql, trigger } = createMockMatchMedia(false);
    window.matchMedia = jest.fn().mockReturnValue(mql);

    const { result } = renderHook(() => useMediaQuery('(min-width: 640px)'));
    expect(result.current).toBe(false);

    act(() => {
      trigger(true);
    });
    expect(result.current).toBe(true);
  });
});
