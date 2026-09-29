import { renderHook, act, waitFor } from '@testing-library/react';
import { useCombinePolling } from '@/lib/hooks/useCombinePolling';

function response(status: number, body: unknown = {}, etag: string | null = null) {
  return {
    // A real Response is not `ok` for a 304 — the hook has to read the status.
    ok: status >= 200 && status < 300,
    status,
    headers: { get: (k: string) => (k.toLowerCase() === 'etag' ? etag : null) },
    json: async () => body,
  };
}

function mockFetchOk(body: unknown, etag = 'W/"abc"') {
  return jest.fn().mockResolvedValue(response(200, body, etag));
}

function setHidden(hidden: boolean) {
  Object.defineProperty(document, 'hidden', { configurable: true, value: hidden });
  document.dispatchEvent(new Event('visibilitychange'));
}

describe('useCombinePolling', () => {
  const realFetch = global.fetch;

  afterEach(() => {
    global.fetch = realFetch;
    jest.useRealTimers();
    setHidden(false);
    jest.clearAllMocks();
  });

  it('exposes the payload after a successful fetch', async () => {
    global.fetch = mockFetchOk({ event_name: 'Combine' }) as unknown as typeof fetch;
    const { result } = renderHook(() => useCombinePolling<{ event_name: string }>('/board'));

    await waitFor(() => expect(result.current.data).toEqual({ event_name: 'Combine' }));
    expect(result.current.error).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it('sends If-None-Match once it has an ETag', async () => {
    const fetchMock = mockFetchOk({ ok: 1 }, 'W/"v1"');
    global.fetch = fetchMock as unknown as typeof fetch;
    const { result } = renderHook(() => useCombinePolling('/board'));

    await waitFor(() => expect(result.current.data).not.toBeNull());
    act(() => result.current.refresh());

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const [, options] = fetchMock.mock.calls[1];
    expect((options.headers as Record<string, string>)['If-None-Match']).toBe('W/"v1"');
  });

  it('keeps the board on an unchanged 304', async () => {
    const fetchMock = jest
      .fn()
      .mockResolvedValueOnce(response(200, { event_name: 'Combine' }, 'W/"v1"'))
      .mockResolvedValue(response(304));
    global.fetch = fetchMock as unknown as typeof fetch;

    const { result } = renderHook(() => useCombinePolling<{ event_name: string }>('/board'));
    await waitFor(() => expect(result.current.data).not.toBeNull());

    act(() => result.current.refresh());
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));

    expect(result.current.data).toEqual({ event_name: 'Combine' });
    expect(result.current.error).toBeNull();
  });

  it('keeps the last good board on screen when a poll fails', async () => {
    const fetchMock = jest
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: { get: () => null },
        json: async () => ({ event_name: 'Combine' }),
      })
      .mockRejectedValue(new Error('network down'));
    global.fetch = fetchMock as unknown as typeof fetch;

    const { result } = renderHook(() => useCombinePolling<{ event_name: string }>('/board'));
    await waitFor(() => expect(result.current.data).not.toBeNull());

    act(() => result.current.refresh());
    await waitFor(() => expect(result.current.error).not.toBeNull());

    // The board must never blank out — a stale number beats an empty screen,
    // provided the staleness is visible.
    expect(result.current.data).toEqual({ event_name: 'Combine' });
  });

  it('treats a 429 as transient rather than fatal', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 429,
      headers: { get: () => null },
      json: async () => ({}),
    }) as unknown as typeof fetch;

    const { result } = renderHook(() => useCombinePolling('/board'));
    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.error).not.toMatch(/expired/i);
  });

  it('explains an expired link on a 404', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 404,
      headers: { get: () => null },
      json: async () => ({}),
    }) as unknown as typeof fetch;

    const { result } = renderHook(() => useCombinePolling('/board'));
    await waitFor(() => expect(result.current.error).toMatch(/expired/i));
  });

  it('holds the board through a single 404, which may be a blip', async () => {
    const fetchMock = jest
      .fn()
      .mockResolvedValueOnce(response(200, { event_name: 'Combine' }))
      .mockResolvedValue(response(404));
    global.fetch = fetchMock as unknown as typeof fetch;

    const { result } = renderHook(() => useCombinePolling<{ event_name: string }>('/board'));
    await waitFor(() => expect(result.current.data).not.toBeNull());

    act(() => result.current.refresh());
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(result.current.data).not.toBeNull();

    act(() => result.current.refresh());
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    expect(result.current.data).not.toBeNull();
  });

  it('clears the board after three consecutive 404s, so Turn off empties the TV', async () => {
    const fetchMock = jest
      .fn()
      .mockResolvedValueOnce(response(200, { event_name: 'Combine' }, 'W/"v1"'))
      .mockResolvedValueOnce(response(404))
      .mockResolvedValueOnce(response(404))
      .mockResolvedValueOnce(response(404))
      .mockResolvedValue(response(200, { event_name: 'Combine again' }, 'W/"v2"'));
    global.fetch = fetchMock as unknown as typeof fetch;

    const { result } = renderHook(() => useCombinePolling<{ event_name: string }>('/board'));
    await waitFor(() => expect(result.current.data).not.toBeNull());

    act(() => result.current.refresh());
    act(() => result.current.refresh());
    act(() => result.current.refresh());

    // Turn off is the only way to take minors' names off a screen in a public hall.
    await waitFor(() => expect(result.current.data).toBeNull());
    expect(result.current.lastUpdated).toBeNull();

    // And it keeps polling, so a restored link comes back without anyone touching
    // the TV — with no stale ETag, which would otherwise answer 304 and show nothing.
    act(() => result.current.refresh());
    await waitFor(() => expect(result.current.data).toEqual({ event_name: 'Combine again' }));
    const [, recovery] = fetchMock.mock.calls[fetchMock.mock.calls.length - 1];
    expect((recovery.headers as Record<string, string>)['If-None-Match']).toBeUndefined();
  });

  it('starts the 404 count again after a good poll', async () => {
    const fetchMock = jest
      .fn()
      .mockResolvedValueOnce(response(200, { event_name: 'Combine' }))
      .mockResolvedValueOnce(response(404))
      .mockResolvedValueOnce(response(404))
      .mockResolvedValueOnce(response(200, { event_name: 'Combine' }))
      .mockResolvedValue(response(404));
    global.fetch = fetchMock as unknown as typeof fetch;

    const { result } = renderHook(() => useCombinePolling<{ event_name: string }>('/board'));
    await waitFor(() => expect(result.current.data).not.toBeNull());

    for (let poll = 0; poll < 4; poll += 1) {
      act(() => result.current.refresh());
      // eslint-disable-next-line no-await-in-loop
      await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(poll + 2));
    }

    // Two 404s, a good poll, then two more 404s is a flaky link, not a turned-off board.
    expect(result.current.data).not.toBeNull();
  });

  it('starts the 404 count again after a network failure, which is not a revoked link', async () => {
    // A Supabase wobble reaches the kiosk as a rejected fetch, not a 404, so 404s
    // either side of one are not consecutive. Letting them accumulate across it
    // clears a TV in a full hall on a link nobody revoked — and the coach's only
    // visible remedy, New link, is the wrong action.
    const fetchMock = jest
      .fn()
      .mockResolvedValueOnce(response(200, { event_name: 'Combine' }))
      .mockResolvedValueOnce(response(404))
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce(response(404))
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValue(response(404));
    global.fetch = fetchMock as unknown as typeof fetch;

    const { result } = renderHook(() => useCombinePolling<{ event_name: string }>('/board'));
    await waitFor(() => expect(result.current.data).not.toBeNull());

    for (let poll = 0; poll < 5; poll += 1) {
      act(() => result.current.refresh());
      // eslint-disable-next-line no-await-in-loop
      await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(poll + 2));
    }

    expect(result.current.data).not.toBeNull();
  });

  it('does not treat a superseded request as a failure', async () => {
    const fetchMock = jest
      .fn()
      .mockImplementationOnce(
        (_url: string, options: RequestInit) =>
          new Promise((_resolve, reject) => {
            options.signal?.addEventListener('abort', () => {
              // Reject on a macrotask, so the rejection lands after the newer
              // request has resolved — the ordering that left "Aborted" on the wall.
              setTimeout(() => reject(new DOMException('Aborted', 'AbortError')), 0);
            });
          })
      )
      .mockResolvedValue(response(200, { event_name: 'Combine' }));
    global.fetch = fetchMock as unknown as typeof fetch;

    const { result } = renderHook(() => useCombinePolling<{ event_name: string }>('/board'));
    act(() => result.current.refresh());
    await waitFor(() => expect(result.current.data).not.toBeNull());

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 5));
    });

    expect(result.current.error).toBeNull();
  });

  it('does not advance the stale clock while the tab is hidden', async () => {
    // Fake timers go in before render: the hook starts its one-second clock on
    // mount, and installing them afterwards leaves that interval on the real one.
    jest.useFakeTimers();
    global.fetch = mockFetchOk({ ok: 1 }) as unknown as typeof fetch;
    const { result } = renderHook(() => useCombinePolling('/board'));
    await waitFor(() => expect(result.current.data).not.toBeNull());

    // Polling is deliberately paused when hidden, so letting the clock run would
    // show RECONNECTING for a board that is simply behind another window.
    setHidden(true);
    act(() => {
      jest.advanceTimersByTime(60_000);
    });

    expect(result.current.staleSeconds).toBe(0);
  });
});
