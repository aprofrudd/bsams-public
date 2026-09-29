'use client';

import { useState, useEffect, useCallback } from 'react';

const STORAGE_KEY = 'bsams-cookie-consent';

export function CookieBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    try {
      if (!localStorage.getItem(STORAGE_KEY)) {
        setVisible(true);
      }
    } catch { /* ignore */ }
  }, []);

  const dismiss = useCallback(() => {
    setVisible(false);
    try { localStorage.setItem(STORAGE_KEY, '1'); } catch { /* ignore */ }
  }, []);

  if (!visible) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 p-3 sm:p-4">
      <div className="max-w-4xl mx-auto card flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:gap-4 p-4">
        <p className="text-sm text-white/80 flex-1">
          We use essential cookies to keep you signed in. No tracking or advertising cookies are used.{' '}
          <a href="/cookies" className="text-[#33CBF4] hover:underline">Learn more</a>
        </p>
        <button
          onClick={dismiss}
          className="px-4 py-1.5 text-sm font-medium rounded bg-[#33CBF4] text-[#090A3D] hover:bg-[#33CBF4]/80 transition-colors whitespace-nowrap"
        >
          OK
        </button>
      </div>
    </div>
  );
}
