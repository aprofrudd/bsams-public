'use client';

import { useState, useEffect, useCallback } from 'react';

const STORAGE_KEY = 'bsams-onboarding';

interface OnboardingState {
  completedAt: string | null;
  dismissedAt: string | null;
  currentStep: number;
  athleteCreated: boolean;
}

const DEFAULT_STATE: OnboardingState = {
  completedAt: null,
  dismissedAt: null,
  currentStep: 0,
  athleteCreated: false,
};

function readStorage(): OnboardingState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_STATE;
    return { ...DEFAULT_STATE, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_STATE;
  }
}

function writeStorage(state: OnboardingState) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // Private browsing or quota exceeded — silently ignore
  }
}

export interface UseOnboardingReturn {
  isWizardOpen: boolean;
  showResumeBanner: boolean;
  currentStep: number;
  athleteCreated: boolean;
  openWizard: () => void;
  dismissWizard: () => void;
  nextStep: () => void;
  prevStep: () => void;
  markAthleteCreated: () => void;
  completeOnboarding: () => void;
}

export function useOnboarding(userRole: string | null | undefined): UseOnboardingReturn {
  const [state, setState] = useState<OnboardingState>(DEFAULT_STATE);
  const [hydrated, setHydrated] = useState(false);
  const [wizardOpenOverride, setWizardOpenOverride] = useState(false);

  // Hydrate from localStorage on client
  useEffect(() => {
    setState(readStorage());
    setHydrated(true);
  }, []);

  const isCoachOrAdmin = userRole === 'coach' || userRole === 'admin';

  const isWizardOpen = hydrated && isCoachOrAdmin && !state.completedAt && (
    !state.dismissedAt || wizardOpenOverride
  );

  const showResumeBanner = hydrated && isCoachOrAdmin && !state.completedAt && !!state.dismissedAt && !wizardOpenOverride;

  const update = useCallback((partial: Partial<OnboardingState>) => {
    setState(prev => {
      const next = { ...prev, ...partial };
      writeStorage(next);
      return next;
    });
  }, []);

  const openWizard = useCallback(() => {
    setWizardOpenOverride(true);
  }, []);

  const dismissWizard = useCallback(() => {
    setWizardOpenOverride(false);
    update({ dismissedAt: new Date().toISOString() });
  }, [update]);

  const nextStep = useCallback(() => {
    setState(prev => {
      const next = { ...prev, currentStep: Math.min(prev.currentStep + 1, 2) };
      writeStorage(next);
      return next;
    });
  }, []);

  const prevStep = useCallback(() => {
    setState(prev => {
      const next = { ...prev, currentStep: Math.max(prev.currentStep - 1, 0) };
      writeStorage(next);
      return next;
    });
  }, []);

  const markAthleteCreated = useCallback(() => {
    update({ athleteCreated: true });
  }, [update]);

  const completeOnboarding = useCallback(() => {
    setWizardOpenOverride(false);
    update({ completedAt: new Date().toISOString() });
  }, [update]);

  return {
    isWizardOpen,
    showResumeBanner,
    currentStep: state.currentStep,
    athleteCreated: state.athleteCreated,
    openWizard,
    dismissWizard,
    nextStep,
    prevStep,
    markAthleteCreated,
    completeOnboarding,
  };
}
