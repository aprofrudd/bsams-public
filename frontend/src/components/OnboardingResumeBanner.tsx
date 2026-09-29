'use client';

interface OnboardingResumeBannerProps {
  onResume: () => void;
  onDismissPermanently: () => void;
}

export function OnboardingResumeBanner({ onResume, onDismissPermanently }: OnboardingResumeBannerProps) {
  return (
    <div className="bg-accent/10 border-b border-accent/20 w-full">
      <div className="max-w-7xl mx-auto px-3 sm:px-4 md:px-6 py-2 flex items-center justify-between gap-3">
        <p className="text-white/70 text-xs sm:text-sm flex-1">
          Complete your account setup to get the most out of BSAMS
        </p>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={onResume}
            className="text-accent font-semibold text-xs sm:text-sm hover:text-accent/80 transition-colors min-h-[44px] px-2 flex items-center"
          >
            Resume Setup
          </button>
          <button
            onClick={onDismissPermanently}
            className="text-white/30 hover:text-white/60 transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
            aria-label="Dismiss permanently"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
