export default function TermsPage() {
  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="section-title text-2xl mb-6">Terms of Service</h1>
      <div className="card prose prose-invert max-w-none">
        <p className="text-white/60 text-sm mb-6">Last updated: February 2026</p>

        <h2 className="text-lg font-heading text-white mb-3">1. Acceptance of Terms</h2>
        <p className="text-white/80 mb-4">
          By accessing or using BSAMS (Boxing Science Athlete Management System), you agree to be bound by these
          Terms of Service. If you do not agree, you may not use the service.
        </p>

        <h2 className="text-lg font-heading text-white mb-3">2. Service Description</h2>
        <p className="text-white/80 mb-4">
          BSAMS is an athlete management platform that enables coaches and athletes to track performance metrics,
          training sessions, wellness data, and other health-related information.
        </p>

        <h2 className="text-lg font-heading text-white mb-3">3. User Responsibilities</h2>
        <p className="text-white/80 mb-2">As a user of BSAMS, you agree to:</p>
        <ul className="list-disc list-inside text-white/80 mb-4 space-y-1">
          <li>Provide accurate and complete information</li>
          <li>Maintain the security of your account credentials</li>
          <li>Use the service in compliance with applicable laws</li>
          <li>Not attempt to access data belonging to other users</li>
          <li>Not use the service for any unlawful purpose</li>
        </ul>

        <h2 className="text-lg font-heading text-white mb-3">4. Intellectual Property</h2>
        <p className="text-white/80 mb-4">
          [Details on intellectual property rights, ownership of content, and usage rights will go here]
        </p>

        <h2 className="text-lg font-heading text-white mb-3">5. Limitation of Liability</h2>
        <p className="text-white/80 mb-4">
          [Details on limitation of liability, warranty disclaimers, and indemnification will go here]
        </p>

        <h2 className="text-lg font-heading text-white mb-3">6. Termination</h2>
        <p className="text-white/80 mb-4">
          Either party may terminate use of the service at any time. Upon termination, you may request
          export of your data in accordance with our Privacy Policy. We reserve the right to suspend or
          terminate accounts that violate these terms.
        </p>

        <h2 className="text-lg font-heading text-white mb-3">7. Governing Law</h2>
        <p className="text-white/80 mb-4">
          [Applicable jurisdiction and governing law will go here]
        </p>

        <h2 className="text-lg font-heading text-white mb-3">8. Contact Information</h2>
        <p className="text-white/80 mb-4">
          [Contact details for questions about these terms will go here]
        </p>
      </div>
    </div>
  );
}
