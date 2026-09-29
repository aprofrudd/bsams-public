export default function CookiePolicyPage() {
  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="section-title text-2xl mb-6">Cookie Policy</h1>
      <div className="card prose prose-invert max-w-none">
        <p className="text-white/60 text-sm mb-6">Last updated: March 2026</p>

        <h2 className="text-lg font-heading text-white mb-3">1. What Are Cookies</h2>
        <p className="text-white/80 mb-4">
          Cookies are small text files stored on your device by your web browser. This policy also covers
          similar technologies we use, including browser localStorage and the Cache API (used by our
          service worker for offline support).
        </p>

        <h2 className="text-lg font-heading text-white mb-3">2. Cookies We Use</h2>
        <p className="text-white/80 mb-2">
          We use a single cookie, which is strictly necessary for the service to function:
        </p>
        <div className="overflow-x-auto mb-4">
          <table className="w-full text-sm text-white/80">
            <thead>
              <tr className="border-b border-white/10 text-left">
                <th className="py-2 pr-4 font-medium text-white">Name</th>
                <th className="py-2 pr-4 font-medium text-white">Purpose</th>
                <th className="py-2 pr-4 font-medium text-white">Type</th>
                <th className="py-2 pr-4 font-medium text-white">Duration</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-white/5">
                <td className="py-2 pr-4 font-mono text-xs">access_token</td>
                <td className="py-2 pr-4">Keeps you signed in (authentication)</td>
                <td className="py-2 pr-4">HttpOnly, Secure, SameSite=Lax</td>
                <td className="py-2 pr-4">24 hours</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="text-white/80 mb-4">
          This cookie is set as HttpOnly (not accessible to JavaScript), Secure (only sent over HTTPS),
          and SameSite=Lax (not sent with cross-site requests). It contains an authentication token
          and no other personal data.
        </p>

        <h2 className="text-lg font-heading text-white mb-3">3. Local Storage</h2>
        <p className="text-white/80 mb-2">
          We use browser localStorage to remember your preferences. These are not cookies and are never
          sent to our servers. All entries are functional and required for a good user experience:
        </p>
        <div className="overflow-x-auto mb-4">
          <table className="w-full text-sm text-white/80">
            <thead>
              <tr className="border-b border-white/10 text-left">
                <th className="py-2 pr-4 font-medium text-white">Key</th>
                <th className="py-2 pr-4 font-medium text-white">Purpose</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-white/5">
                <td className="py-2 pr-4 font-mono text-xs">bsams-selected-athlete</td>
                <td className="py-2 pr-4">Remembers which athlete you last selected</td>
              </tr>
              <tr className="border-b border-white/5">
                <td className="py-2 pr-4 font-mono text-xs">bsams-onboarding</td>
                <td className="py-2 pr-4">Tracks onboarding wizard progress</td>
              </tr>
              <tr className="border-b border-white/5">
                <td className="py-2 pr-4 font-mono text-xs">bsams-welcome-dismissed</td>
                <td className="py-2 pr-4">Remembers if you dismissed the welcome banner</td>
              </tr>
              <tr className="border-b border-white/5">
                <td className="py-2 pr-4 font-mono text-xs">bsams-cookie-consent</td>
                <td className="py-2 pr-4">Remembers if you dismissed the cookie notice</td>
              </tr>
              <tr className="border-b border-white/5">
                <td className="py-2 pr-4 font-mono text-xs">bsams-training-view</td>
                <td className="py-2 pr-4">Remembers your preferred training page view</td>
              </tr>
              <tr className="border-b border-white/5">
                <td className="py-2 pr-4 font-mono text-xs">bsams-load-toggles</td>
                <td className="py-2 pr-4">Remembers training load chart toggle preferences</td>
              </tr>
              <tr className="border-b border-white/5">
                <td className="py-2 pr-4 font-mono text-xs">bsams-analysis-toggles</td>
                <td className="py-2 pr-4">Remembers analysis chart toggle preferences</td>
              </tr>
            </tbody>
          </table>
        </div>

        <h2 className="text-lg font-heading text-white mb-3">4. Offline Cache</h2>
        <p className="text-white/80 mb-4">
          Our service worker uses the browser Cache API to store static assets (HTML pages, stylesheets,
          scripts, and images) for offline access. No personal data is cached. You can clear this cache
          at any time through your browser settings.
        </p>

        <h2 className="text-lg font-heading text-white mb-3">5. Third-Party Cookies</h2>
        <p className="text-white/80 mb-4">
          We do not use any third-party cookies. There are no analytics, advertising, or social media
          cookies on this site.
        </p>

        <h2 className="text-lg font-heading text-white mb-3">6. Managing Cookies</h2>
        <p className="text-white/80 mb-2">
          You can control cookies through your browser settings. Most browsers allow you to:
        </p>
        <ul className="list-disc list-inside text-white/80 mb-4 space-y-1">
          <li>View and delete existing cookies</li>
          <li>Block all or specific cookies</li>
          <li>Clear localStorage and cached data</li>
        </ul>
        <p className="text-white/80 mb-4">
          Please note that blocking the <span className="font-mono text-xs">access_token</span> cookie
          will prevent you from signing in to BSAMS.
        </p>

        <h2 className="text-lg font-heading text-white mb-3">7. More Information</h2>
        <p className="text-white/80 mb-4">
          For details on how we handle your personal data, see our{' '}
          <a href="/privacy" className="text-[#33CBF4] hover:underline">Privacy Policy</a>.
        </p>
      </div>
    </div>
  );
}
