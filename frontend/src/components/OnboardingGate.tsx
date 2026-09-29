'use client';

import { useAuth } from '@/lib/auth';
import { useAthleteContext } from '@/lib/contexts/AthleteContext';
import { useOnboarding } from '@/lib/hooks/useOnboarding';
import { OnboardingWizard } from './OnboardingWizard';
import { OnboardingResumeBanner } from './OnboardingResumeBanner';
import type { Athlete } from '@/lib/types';

export function OnboardingGate() {
  const { user } = useAuth();
  const { setSelectedAthlete, bumpAthleteVersion } = useAthleteContext();
  const onboarding = useOnboarding(user?.role);

  function handleAthleteCreated(athlete: Athlete) {
    setSelectedAthlete(athlete);
    bumpAthleteVersion();
    onboarding.markAthleteCreated();
    // Auto-advance to tour step after brief delay
    setTimeout(() => {
      onboarding.nextStep();
    }, 1200);
  }

  return (
    <>
      {onboarding.showResumeBanner && (
        <OnboardingResumeBanner
          onResume={onboarding.openWizard}
          onDismissPermanently={onboarding.completeOnboarding}
        />
      )}
      {onboarding.isWizardOpen && (
        <OnboardingWizard
          currentStep={onboarding.currentStep}
          athleteCreated={onboarding.athleteCreated}
          onNext={onboarding.nextStep}
          onPrev={onboarding.prevStep}
          onDismiss={onboarding.dismissWizard}
          onAthleteCreated={handleAthleteCreated}
          onComplete={onboarding.completeOnboarding}
        />
      )}
    </>
  );
}
