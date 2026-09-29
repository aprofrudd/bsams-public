export default function PrivacyPage() {
  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="section-title text-2xl mb-6">Privacy Policy</h1>
      <div className="card prose prose-invert max-w-none">
        <p className="text-white/60 text-sm mb-6">Last updated: February 2026</p>

        <h2 className="text-lg font-heading text-white mb-3">1. Data Controller</h2>
        <p className="text-white/80 mb-4">[Your company name and contact details will go here]</p>

        <h2 className="text-lg font-heading text-white mb-3">2. Data We Collect</h2>
        <p className="text-white/80 mb-2">We collect and process the following personal data:</p>
        <ul className="list-disc list-inside text-white/80 mb-4 space-y-1">
          <li>Account information (name, email address)</li>
          <li>Physical measurements (body mass, stature)</li>
          <li>Health and fitness data (performance metrics, wellness scores, training data)</li>
          <li>Assessment photos (movement screening images)</li>
          <li>Usage data (login times, actions performed)</li>
        </ul>

        <h2 className="text-lg font-heading text-white mb-3">3. Cookies &amp; Similar Technologies</h2>
        <p className="text-white/80 mb-4">
          We use one essential cookie for authentication and browser localStorage for UI preferences.
          No tracking, advertising, or third-party cookies are used. For full details, see our{' '}
          <a href="/cookies" className="text-[#33CBF4] hover:underline">Cookie Policy</a>.
        </p>

        <h2 className="text-lg font-heading text-white mb-3">4. Lawful Basis for Processing</h2>
        <p className="text-white/80 mb-4">
          We process your health and fitness data based on your <strong>explicit consent</strong> (GDPR Article 9(2)(a)).
          You may withdraw consent at any time through your account settings.
        </p>

        <h2 className="text-lg font-heading text-white mb-3">5. How We Use Your Data</h2>
        <p className="text-white/80 mb-4">[Details on data usage purposes will go here]</p>

        <h2 className="text-lg font-heading text-white mb-3">6. Data Sharing</h2>
        <p className="text-white/80 mb-2">Your data may be processed by the following sub-processors:</p>
        <ul className="list-disc list-inside text-white/80 mb-4 space-y-1">
          <li>Supabase (database hosting)</li>
          <li>Railway (backend hosting)</li>
          <li>Vercel (frontend hosting)</li>
        </ul>

        <h2 className="text-lg font-heading text-white mb-3">7. Data Retention</h2>
        <p className="text-white/80 mb-4">[Data retention periods will go here]</p>

        <h2 className="text-lg font-heading text-white mb-3">8. Your Rights</h2>
        <p className="text-white/80 mb-2">Under GDPR, you have the right to:</p>
        <ul className="list-disc list-inside text-white/80 mb-4 space-y-1">
          <li>Access your personal data</li>
          <li>Rectify inaccurate data</li>
          <li>Erase your data (&quot;right to be forgotten&quot;)</li>
          <li>Export your data in a portable format</li>
          <li>Withdraw consent at any time</li>
          <li>Lodge a complaint with a supervisory authority</li>
        </ul>

        <h2 className="text-lg font-heading text-white mb-3">9. Contact &amp; Complaints</h2>
        <p className="text-white/80 mb-4">
          [Contact information for data controller and relevant supervisory authority (ICO for UK, relevant DPA for EU) will go here]
        </p>
      </div>
    </div>
  );
}
