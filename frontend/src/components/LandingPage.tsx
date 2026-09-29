'use client';

import Link from 'next/link';

const FEATURES = [
  {
    title: 'PERFORMANCE TESTING',
    description: 'Jump, VBT, lactate, mobility, isometric, and air bike assessments — all in one place.',
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-8 h-8">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
      </svg>
    ),
  },
  {
    title: 'TRAINING MANAGEMENT',
    description: 'Session logging, exercise prescriptions, conditioning intervals, and wellness tracking.',
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-8 h-8">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15a2.25 2.25 0 012.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
      </svg>
    ),
  },
  {
    title: 'LOAD MONITORING',
    description: 'ACWR, monotony, strain, and readiness indicators to keep athletes in the optimal training zone.',
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-8 h-8">
        <path strokeLinecap="round" strokeLinejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z" />
      </svg>
    ),
  },
  {
    title: 'DATA ANALYTICS',
    description: 'Z-scores, benchmarks, radar plots, and trend charts for evidence-based decision making.',
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-8 h-8">
        <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 14.25v2.25m3-4.5v4.5m3-6.75v6.75m3-9v9M6 20.25h12A2.25 2.25 0 0020.25 18V6A2.25 2.25 0 0018 3.75H6A2.25 2.25 0 003.75 6v12A2.25 2.25 0 006 20.25z" />
      </svg>
    ),
  },
  {
    title: 'ATHLETE PORTAL',
    description: 'Athletes view their own data, log sessions and wellness, and complete assigned workouts.',
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-8 h-8">
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
      </svg>
    ),
  },
  {
    title: 'PDF REPORTS',
    description: 'Consolidated test reports across all modalities with one-click PDF export.',
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-8 h-8">
        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
      </svg>
    ),
  },
];

const STEPS = [
  {
    number: '1',
    title: 'CREATE ATHLETES',
    description: 'Add your roster manually, upload via CSV, or invite athletes to self-register.',
  },
  {
    number: '2',
    title: 'TRACK EVERYTHING',
    description: 'Log training sessions, wellness scores, and performance tests across all modalities.',
  },
  {
    number: '3',
    title: 'ANALYSE & REPORT',
    description: 'Benchmark against population data, track trends over time, and export PDF reports.',
  },
];

export function LandingPage() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6">
      {/* Hero */}
      <section className="py-16 sm:py-24 text-center">
        <h2 className="font-heading text-4xl sm:text-5xl md:text-6xl font-bold text-white tracking-tight leading-tight">
          THE SCIENCE BEHIND<br />
          <span className="text-accent">THE PUNCH</span>
        </h2>
        <p className="mt-6 text-lg sm:text-xl text-white/60 max-w-2xl mx-auto leading-relaxed">
          A complete athlete management platform for strength &amp; conditioning coaches.
          Test, train, monitor, and report — all in one system.
        </p>
        <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link href="/login" className="btn-primary text-base px-8 py-3 min-h-[48px]">
            Get Started
          </Link>
          <a
            href="#features"
            className="btn-secondary text-base px-8 py-3 min-h-[48px]"
          >
            Learn More
          </a>
        </div>
        <div className="mt-12 mx-auto w-48 h-px bg-gradient-to-r from-transparent via-accent/50 to-transparent" />
      </section>

      {/* Features */}
      <section id="features" className="py-16 sm:py-20 scroll-mt-20">
        <h3 className="font-heading text-2xl sm:text-3xl font-bold text-white text-center mb-4">
          EVERYTHING YOU NEED
        </h3>
        <p className="text-white/50 text-center mb-12 max-w-lg mx-auto">
          From testing to training to reporting — built for high-performance environments.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {FEATURES.map((feature) => (
            <div key={feature.title} className="card hover:border-accent/30 transition-colors">
              <div className="text-accent mb-4">{feature.icon}</div>
              <h4 className="font-heading text-lg font-semibold text-white mb-2">
                {feature.title}
              </h4>
              <p className="text-white/60 text-sm leading-relaxed">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* How It Works */}
      <section className="py-16 sm:py-20">
        <h3 className="font-heading text-2xl sm:text-3xl font-bold text-white text-center mb-4">
          HOW IT WORKS
        </h3>
        <p className="text-white/50 text-center mb-12 max-w-lg mx-auto">
          Get up and running in minutes.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
          {STEPS.map((step) => (
            <div key={step.number} className="text-center">
              <div className="w-14 h-14 mx-auto mb-4 rounded-full border-2 border-accent flex items-center justify-center">
                <span className="font-heading text-xl font-bold text-accent">{step.number}</span>
              </div>
              <h4 className="font-heading text-lg font-semibold text-white mb-2">
                {step.title}
              </h4>
              <p className="text-white/60 text-sm leading-relaxed">
                {step.description}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-16 sm:py-20 text-center border-t border-secondary-muted">
        <h3 className="font-heading text-2xl sm:text-3xl font-bold text-white mb-4">
          READY TO TRAIN SMARTER?
        </h3>
        <p className="text-white/50 mb-8 max-w-md mx-auto">
          Join coaches using BSAMS to drive performance with data.
        </p>
        <Link href="/login" className="btn-primary text-base px-8 py-3 min-h-[48px]">
          Get Started
        </Link>
        <p className="mt-4 text-white/30 text-xs">
          Free to try. No credit card required.
        </p>
      </section>
    </div>
  );
}
