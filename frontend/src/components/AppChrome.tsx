'use client';

import { usePathname } from 'next/navigation';
import { AppHeader } from '@/components/AppHeader';
import { OnboardingGate } from '@/components/OnboardingGate';
import { ConsentGate } from '@/components/ConsentGate';
import { CookieBanner } from '@/components/CookieBanner';

/**
 * Routes that render without any application chrome.
 *
 * The combine kiosk is a full-bleed board on a gym TV: a sticky 56px header,
 * a max-w-7xl gutter and a cookie banner across the bottom would all eat space
 * that the numbers need. `usePathname` resolves during SSR of client components,
 * so this hides the chrome without the flash the createPortal approach has.
 */
const BARE_ROUTES = ['/combine/live'];

export function AppChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isBare = BARE_ROUTES.some((route) => pathname?.startsWith(route));

  if (isBare) {
    return <>{children}</>;
  }

  return (
    <>
      <AppHeader />
      <OnboardingGate />
      <ConsentGate>
        <main className="max-w-7xl mx-auto px-3 sm:px-4 md:px-6 py-3 sm:py-4 md:py-6">
          {children}
        </main>
      </ConsentGate>
      <footer className="max-w-7xl mx-auto px-3 sm:px-4 md:px-6 py-4 mt-8 border-t border-white/10">
        <div className="flex gap-4 text-xs text-white/40">
          <a href="/help" className="hover:text-white/60">Help</a>
          <a href="/privacy" className="hover:text-white/60">Privacy Policy</a>
          <a href="/cookies" className="hover:text-white/60">Cookie Policy</a>
          <a href="/terms" className="hover:text-white/60">Terms of Service</a>
        </div>
      </footer>
      <CookieBanner />
    </>
  );
}
