/**
 * The `?next=` return path, accepted only when it is a path on this site.
 *
 * Prefix checks are not enough: `router.replace()` hands the string to the URL
 * parser, which strips tabs, CRs and LFs before resolving, so "/<TAB>//evil.example"
 * survives a `startsWith('//')` test and then navigates to https://evil.example.
 * Resolving against our own origin covers the whole class — control characters,
 * backslashes, mixed encodings, absolute URLs. `new URL()` throws on inputs like
 * "//evil:999999/", and this runs during render, where a throw white-screens /login.
 *
 * It lives here rather than in the login page because a Next page module may only
 * export a default and a few known fields; exporting a helper fails the build.
 */
export function safeNextPath(search: string): string | null {
  const raw = new URLSearchParams(search).get('next');
  if (!raw) return null;
  for (let i = 0; i < raw.length; i += 1) {
    const code = raw.charCodeAt(i);
    if (code <= 0x1f || code === 0x7f) return null;
  }
  try {
    const url = new URL(raw, window.location.origin);
    if (url.origin !== window.location.origin) return null;
    return url.pathname + url.search + url.hash;
  } catch {
    return null;
  }
}
