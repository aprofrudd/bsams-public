'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { LandingPage } from '@/components/LandingPage';

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading) {
      // Intercept Supabase password recovery redirects before routing
      const urlParams = new URLSearchParams(window.location.search);
      const code = urlParams.get('code');
      if (code) {
        router.replace(`/reset-password?code=${encodeURIComponent(code)}`);
        return;
      }
      const hash = window.location.hash;
      if (hash && hash.includes('type=recovery')) {
        router.replace(`/reset-password${hash}`);
        return;
      }

      if (user) {
        if (user.role === 'athlete') {
          router.replace('/dashboard');
        } else {
          router.replace('/training');
        }
      }
    }
  }, [loading, user, router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (user) {
    // Redirecting — show spinner
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return <LandingPage />;
}
