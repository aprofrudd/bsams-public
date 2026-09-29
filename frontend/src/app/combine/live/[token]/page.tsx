import { Suspense } from 'react';
import type { Metadata } from 'next';
import { CombineKiosk } from '@/components/combine/CombineKiosk';

/**
 * A crawler that reached a share token would publish the names of minors, so the board
 * is withheld from indexes here as well as in the next.config.js `X-Robots-Tag` header —
 * the header covers the payload, this covers the rendered page.
 */
export const metadata: Metadata = {
  robots: { index: false, follow: false },
};

/**
 * Public combine board. No authentication — the share token in the path is the
 * only credential, and the API returns a sanitised payload for it.
 *
 * AppChrome hides the app header, gutters and cookie banner on this route so the
 * board fills the screen.
 */
export default function CombineLivePage({ params }: { params: { token: string } }) {
  const { token } = params;

  return (
    <Suspense
      fallback={
        <div className="flex h-screen items-center justify-center bg-primary">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-accent border-t-transparent" />
        </div>
      }
    >
      <CombineKiosk token={token} />
    </Suspense>
  );
}
