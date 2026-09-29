import { ApiError, combineApi, fetchApi, uploadApi } from '@/lib/api';

/**
 * Two station-day behaviours of the API client.
 *
 * A 422 from FastAPI arrives as an array of validation objects. Rendered raw it
 * reaches a station iPad as "[object Object]", which tells the operator nothing
 * about which field the boxer's number was rejected from.
 *
 * And a save with no timeout can leave SAVE spinning for as long as the browser
 * is willing to wait, with the boxer already walking away.
 */

function mockResponse(status: number, body?: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers(),
    json: async () => body,
  } as unknown as Response;
}

const fetchMock = jest.fn();

beforeEach(() => {
  fetchMock.mockReset();
  global.fetch = fetchMock as unknown as typeof fetch;
});

function lastInit(): RequestInit {
  return fetchMock.mock.calls[fetchMock.mock.calls.length - 1][1] as RequestInit;
}

describe('fetchApi validation errors', () => {
  it('names the field a 422 rejected', async () => {
    fetchMock.mockResolvedValue(
      mockResponse(422, {
        detail: [
          {
            type: 'less_than_equal',
            loc: ['body', 'measures', 'height_cm'],
            msg: 'Input should be less than or equal to 90',
          },
        ],
      })
    );

    await expect(fetchApi('/combine/events/e1/attempts', { method: 'POST' })).rejects.toThrow(
      'height_cm: Input should be less than or equal to 90'
    );
  });

  it('joins several field errors into one line', async () => {
    fetchMock.mockResolvedValue(
      mockResponse(422, {
        detail: [
          { loc: ['body', 'measures', 'load_kg'], msg: 'Input should be greater than 0' },
          { loc: ['body', 'measures', 'peak_velocity_ms'], msg: 'Input should be less than or equal to 10' },
        ],
      })
    );

    await expect(fetchApi('/combine/events/e1/attempts', { method: 'POST' })).rejects.toThrow(
      'load_kg: Input should be greater than 0; peak_velocity_ms: Input should be less than or equal to 10'
    );
  });

  it("drops pydantic's Value error prefix from a model validator message", async () => {
    fetchMock.mockResolvedValue(
      mockResponse(422, {
        detail: [
          {
            type: 'value_error',
            loc: ['body', 'measures'],
            msg: 'Value error, Provide flight and contact times, or an RSI value',
          },
        ],
      })
    );

    await expect(fetchApi('/combine/events/e1/attempts', { method: 'POST' })).rejects.toThrow(
      'measures: Provide flight and contact times, or an RSI value'
    );
  });

  it('leaves a plain string detail alone', async () => {
    fetchMock.mockResolvedValue(mockResponse(404, { detail: 'Combine event not found' }));

    const err = (await fetchApi('/combine/events/e1').catch((e) => e)) as ApiError;
    expect(err).toBeInstanceOf(ApiError);
    expect(err.message).toBe('Combine event not found');
    expect(err.status).toBe(404);
  });

  it('flattens a 422 on the CSV upload path too', async () => {
    fetchMock.mockResolvedValue(
      mockResponse(422, {
        detail: [{ loc: ['body', 'file'], msg: 'Field required' }],
      })
    );

    const file = new File(['Test Date\n01/01/2026'], 'events.csv', { type: 'text/csv' });
    await expect(uploadApi.uploadCsv(file)).rejects.toThrow('file: Field required');
  });
});

describe('fetchApi timeout', () => {
  /** A request that never settles until its signal aborts, like a dropped wifi save. */
  function stalledFetch() {
    fetchMock.mockImplementation(
      (_url: string, init?: RequestInit) =>
        new Promise((_resolve, reject) => {
          init?.signal?.addEventListener('abort', () =>
            reject(new DOMException('The operation was aborted.', 'AbortError'))
          );
        })
    );
  }

  it('gives the operator an instruction, not a stack trace', async () => {
    stalledFetch();

    const err = (await fetchApi(
      '/combine/events/e1/attempts',
      { method: 'POST' },
      { timeoutMs: 10 }
    ).catch((e) => e)) as ApiError;
    expect(err).toBeInstanceOf(ApiError);
    expect(err.message).toBe('Timed out — check the connection and tap SAVE again');
  });

  it('never times out a call that did not ask for one', async () => {
    fetchMock.mockResolvedValue(mockResponse(200, { ok: true }));

    await expect(fetchApi('/combine/events')).resolves.toEqual({ ok: true });
    expect(lastInit().signal).toBeUndefined();
  });

  it('bounds the four calls a station operator waits on', async () => {
    fetchMock.mockResolvedValue(mockResponse(200, []));

    await combineApi.submitAttempt('e1', {
      participant_id: 'p1',
      measures: { station: 'cmj', height_cm: 40 },
    });
    expect(lastInit().signal).toBeInstanceOf(AbortSignal);

    await combineApi.stationRoster('e1', 'cmj');
    expect(lastInit().signal).toBeInstanceOf(AbortSignal);

    await combineApi.listAttempts('e1', { participantId: 'p1' });
    expect(lastInit().signal).toBeInstanceOf(AbortSignal);

    fetchMock.mockResolvedValue(mockResponse(204));
    await combineApi.deleteAttempt('a1');
    expect(lastInit().signal).toBeInstanceOf(AbortSignal);
  });
});
