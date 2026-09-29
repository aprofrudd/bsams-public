'use client';

import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';

const EXPERTS = [
  {
    name: 'Consultant A',
    specialism: 'Strength & Power',
    bio: 'Placeholder biography for a strength and power consultant.',
    price: '£XX',
    email: 'consult@example.com',
    subject: 'Consultation Booking — Strength',
  },
  {
    name: 'Consultant B',
    specialism: 'Conditioning & Energy Systems',
    bio: 'Placeholder biography for a conditioning consultant.',
    price: '£XX',
    email: 'consult@example.com',
    subject: 'Consultation Booking — Conditioning',
  },
];

export default function ConsultPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="inline-block w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) {
    router.push('/login');
    return null;
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h2 className="section-title text-base sm:text-lg">Expert Consultation</h2>
      <p className="text-white/60 text-sm">
        Book a 1-on-1 session with one of our experts for personalised advice on your training programme.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        {EXPERTS.map((expert) => (
          <div key={expert.email} className="card border-t-2 border-t-accent">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-full bg-accent/15 flex items-center justify-center shrink-0">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-6 h-6 text-accent">
                  <path d="M10 8a3 3 0 100-6 3 3 0 000 6zM3.465 14.493a1.23 1.23 0 00.41 1.412A9.957 9.957 0 0010 18c2.31 0 4.438-.784 6.131-2.1.43-.333.604-.903.408-1.41a7.002 7.002 0 00-13.074.003z" />
                </svg>
              </div>
              <div>
                <h3 className="font-heading text-sm uppercase tracking-wider text-white">{expert.name}</h3>
                <p className="text-xs text-accent">{expert.specialism}</p>
              </div>
            </div>

            <p className="text-white/60 text-sm mb-4">{expert.bio}</p>

            <div className="flex items-center justify-between">
              <span className="text-white/80 text-sm font-medium">{expert.price} per session</span>
              <a
                href={`mailto:${expert.email}?subject=${encodeURIComponent(expert.subject)}`}
                className="px-4 py-2 min-h-[44px] flex items-center rounded text-sm font-medium bg-accent text-[#090A3D] hover:bg-accent/80 transition-colors"
              >
                Book via Email
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
