import { readFileSync } from 'fs';
import { join } from 'path';

// The kiosk TV has nobody standing at it, so the offline fallback has to recover on
// its own and the board page must stay out of search engines and referrer headers.
// These cover public/offline.html, public/sw.js, next.config.js and the board page.

jest.mock('@/components/combine/CombineKiosk', () => ({ CombineKiosk: () => null }));

const frontendRoot = join(__dirname, '..', '..');
const offlineHtml = readFileSync(join(frontendRoot, 'public', 'offline.html'), 'utf8');
const swSource = readFileSync(join(frontendRoot, 'public', 'sw.js'), 'utf8');

type Listener = () => void;

/**
 * Runs offline.html's inline script with a fake `window`, so the real script text is
 * exercised without fighting jsdom's read-only `location`. The script must reach every
 * global through `window.` for this to hold.
 */
function runRecoveryScript(fetchMock: jest.Mock) {
  const match = offlineHtml.match(/<script>([\s\S]*?)<\/script>/);
  if (!match) throw new Error('offline.html has no inline recovery script');

  const listeners: Record<string, Listener[]> = {};
  const intervals: Array<{ fn: () => void; ms: number }> = [];
  const reload = jest.fn();
  const fakeWindow = {
    location: { href: 'https://bsams.test/combine/live/tok', reload },
    fetch: fetchMock,
    addEventListener: (type: string, fn: Listener) => {
      listeners[type] = (listeners[type] || []).concat(fn);
      return undefined;
    },
    setInterval: (fn: () => void, ms: number) => {
      intervals.push({ fn, ms });
      return intervals.length;
    },
  };

  // eslint-disable-next-line
  new Function('window', match[1])(fakeWindow);

  return {
    reload,
    online: () => (listeners.online || []).forEach((fn) => fn()),
    probe: () => intervals.forEach((timer) => timer.fn()),
    probeIntervalMs: intervals.length ? intervals[0].ms : null,
  };
}

// Lets the probe's fetch promise chain settle (jsdom has no setImmediate).
const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

describe('offline.html recovery', () => {
  it('reloads when the browser comes back online', () => {
    const script = runRecoveryScript(jest.fn());
    script.online();
    expect(script.reload).toHaveBeenCalled();
  });

  it('reloads when a probe of the page succeeds, in case the online event never fires', async () => {
    const fetchMock = jest.fn().mockResolvedValue({ ok: true });
    const script = runRecoveryScript(fetchMock);

    script.probe();
    await flush();

    expect(fetchMock).toHaveBeenCalledWith(
      'https://bsams.test/combine/live/tok',
      expect.objectContaining({ method: 'HEAD' })
    );
    expect(script.reload).toHaveBeenCalled();
  });

  it('keeps waiting when the probe fails', async () => {
    const script = runRecoveryScript(jest.fn().mockRejectedValue(new Error('offline')));

    script.probe();
    await flush();

    expect(script.reload).not.toHaveBeenCalled();
  });

  it('probes about every ten seconds', () => {
    const script = runRecoveryScript(jest.fn());
    // Often enough that the TV is back within a minute of the wifi, rare enough that a
    // long outage does not hammer the origin.
    expect(script.probeIntervalMs).toBeGreaterThanOrEqual(5000);
    expect(script.probeIntervalMs).toBeLessThanOrEqual(15000);
  });

  it('does not promise that unsaved entries survived', () => {
    // A station operator mid-entry loses whatever was typed; saying "nothing has been
    // lost" would send them past a missing result.
    expect(offlineHtml).not.toMatch(/nothing has been lost/i);
    expect(offlineHtml).toContain(
      'Anything typed but not yet saved was not recorded. When you are back online, ' +
        'check what was logged and re-enter anything missing.'
    );
  });
});

describe('sw.js', () => {
  it('names a cache version above the one already installed on devices', () => {
    // Installed iPads and the TV keep serving the cached offline page until the name
    // changes, so the A12 rewrite only reaches them with a bump.
    const match = swSource.match(/const CACHE_NAME = 'bsams-v(\d+)'/);
    expect(match).not.toBeNull();
    expect(Number(match![1])).toBeGreaterThanOrEqual(2);
  });

  it('writes only build assets to the cache, never kiosk HTML', () => {
    // A cached /combine/live/<token> page would serve a stale board after a deploy.
    const staticBranch = swSource.indexOf('/_next/static/');
    expect(staticBranch).toBeGreaterThan(-1);

    const put = /cache\.put\(/g;
    const offsets: number[] = [];
    let hit = put.exec(swSource);
    while (hit) {
      offsets.push(hit.index);
      hit = put.exec(swSource);
    }

    expect(offsets.length).toBeGreaterThan(0);
    offsets.forEach((offset) => expect(offset).toBeGreaterThan(staticBranch));
  });
});

describe('public board headers', () => {
  it('sends noindex and no-referrer for /combine/live/:path*', async () => {
    // eslint-disable-next-line
    const nextConfig = require(join(frontendRoot, 'next.config.js'));
    expect(typeof nextConfig.headers).toBe('function');

    const rules = await nextConfig.headers();
    const board = rules.find(
      (rule: { source: string }) => rule.source === '/combine/live/:path*'
    );
    expect(board).toBeDefined();

    const sent: Record<string, string> = {};
    board.headers.forEach((header: { key: string; value: string }) => {
      sent[header.key.toLowerCase()] = header.value;
    });

    expect(sent['x-robots-tag']).toContain('noindex');
    expect(sent['x-robots-tag']).toContain('nofollow');
    expect(sent['x-robots-tag']).toContain('noarchive');
    expect(sent['referrer-policy']).toBe('no-referrer');
  });

  it('marks the board page noindex in its metadata', () => {
    // A crawler that reaches a share token would publish minors' names.
    // eslint-disable-next-line
    const page = require('@/app/combine/live/[token]/page');
    expect(page.metadata.robots).toEqual(
      expect.objectContaining({ index: false, follow: false })
    );
  });
});
