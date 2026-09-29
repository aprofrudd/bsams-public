'use client';

import { useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { useMetabolicProtocol } from '@/lib/hooks/useMetabolicProtocol';
import { useBleConnection } from '@/lib/hooks/useBleConnection';
import { useWakeLock } from '@/lib/hooks/useWakeLock';
import { useTimerAudio } from '../training/useTimerAudio';
import { MetabolicSetup } from './MetabolicSetup';
import { MetabolicSprint } from './MetabolicSprint';
import { MetabolicRest } from './MetabolicRest';
import { MetabolicSprintEntry } from './MetabolicSprintEntry';
import { MetabolicResults } from './MetabolicResults';
import type { FtmsData } from '@/lib/bleProtocol';

interface MetabolicProfilerProps {
  athleteId: string;
  athleteWeight: number | null;
  onClose: () => void;
  onSaved: () => void;
}

// Phase to progress step mapping
const PHASE_STEPS: Record<string, number> = {
  SETUP: 0, WARMUP: 1,
  COUNTDOWN_1: 2, SPRINT_1: 3, REST_1: 4,
  COUNTDOWN_2: 5, SPRINT_2: 6, REST_2: 7,
  COUNTDOWN_3: 8, SPRINT_3: 9,
  POST_TEST: 10, RESULTS: 11,
  SPRINT_ENTRY: 10,
};

const TOTAL_STEPS = 12;

export function MetabolicProfiler({ athleteId, athleteWeight, onClose, onSaved }: MetabolicProfilerProps) {
  const protocol = useMetabolicProtocol();
  const wakeLock = useWakeLock();
  const audio = useTimerAudio();

  const bleAvailable = typeof window !== 'undefined' && !!navigator.bluetooth;

  // BLE connection with power sample forwarding
  const handleBleData = useCallback((data: FtmsData) => {
    if (data.instantPower != null) {
      protocol.handlePowerSample(data.instantPower);
    }
  }, [protocol]);

  const ble = useBleConnection(handleBleData);

  // Wake lock management
  useEffect(() => {
    const { phase } = protocol.state;
    if (phase === 'COUNTDOWN_1' || phase === 'SPRINT_1' || phase === 'REST_1' ||
        phase === 'COUNTDOWN_2' || phase === 'SPRINT_2' || phase === 'REST_2' ||
        phase === 'COUNTDOWN_3' || phase === 'SPRINT_3' || phase === 'POST_TEST') {
      wakeLock.acquire();
    } else {
      wakeLock.release();
    }
  }, [protocol.state.phase, wakeLock]);

  // Audio cues based on phase changes
  useEffect(() => {
    const { phase, countdown, sprintRemaining } = protocol.state;

    if (phase.startsWith('COUNTDOWN_') && countdown > 0 && countdown <= 3) {
      audio.playCountdownBeep();
    }

    if (phase.startsWith('SPRINT_') && sprintRemaining === 0) {
      audio.playStopBeep();
    }
  }, [protocol.state.phase, protocol.state.countdown, protocol.state.sprintRemaining, audio]);

  // Play go beep when sprint starts
  useEffect(() => {
    const { phase } = protocol.state;
    if (phase === 'SPRINT_1' || phase === 'SPRINT_2' || phase === 'SPRINT_3') {
      audio.playGoBeep();
    }
  }, [protocol.state.phase, audio]);

  const handleClose = useCallback(() => {
    const { phase } = protocol.state;
    if (phase !== 'INACTIVE' && phase !== 'SETUP' && phase !== 'RESULTS') {
      if (!confirm('Abandon the current protocol? All data will be lost.')) return;
    }
    protocol.reset();
    wakeLock.release();
    ble.disconnect();
    onClose();
  }, [protocol, wakeLock, ble, onClose]);

  const handleSaved = useCallback(() => {
    onSaved();
  }, [onSaved]);

  const { phase } = protocol.state;
  const currentStep = PHASE_STEPS[phase] ?? -1;

  // Get live power for sprint display
  const livePower = ble.liveData?.instantPower ?? null;

  // Current sprint samples
  const currentSprintSamples =
    phase === 'SPRINT_1' ? protocol.state.sprint1Samples :
    phase === 'SPRINT_2' ? protocol.state.sprint2Samples :
    phase === 'SPRINT_3' ? protocol.state.sprint3Samples :
    [];

  const overlay = (
    <div className="fixed inset-0 z-[100] bg-primary flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-secondary-muted/30">
        <h1 className="text-sm font-heading uppercase tracking-wider text-accent">
          Metabolic Profiling
        </h1>
        <button
          onClick={handleClose}
          className="text-white/40 hover:text-white p-2 min-h-[44px] min-w-[44px] flex items-center justify-center transition-colors"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
            <path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
          </svg>
        </button>
      </div>

      {/* Progress bar */}
      <div className="flex gap-0.5 px-4 py-2">
        {Array.from({ length: TOTAL_STEPS }, (_, i) => (
          <div
            key={i}
            className={`flex-1 h-1 rounded-full transition-colors ${
              i < currentStep ? 'bg-accent' :
              i === currentStep ? 'bg-red-400' :
              'bg-secondary-muted/30'
            }`}
          />
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {/* SETUP */}
        {phase === 'INACTIVE' || phase === 'SETUP' ? (
          <MetabolicSetup
            defaultWeight={athleteWeight}
            onBegin={(config) => {
              audio.initAudio();
              protocol.beginProtocol(config);
            }}
            bleAvailable={bleAvailable}
          />
        ) : null}

        {/* WARMUP */}
        {phase === 'WARMUP' && (
          <div className="text-center space-y-6 max-w-sm mx-auto">
            <h2 className="text-xl font-heading font-bold">Warm Up</h2>
            <p className="text-sm text-white/50">
              Warm up for 5-10 minutes at a comfortable pace. When ready, press Start.
            </p>
            {protocol.state.config?.dataSource === 'ble' && (
              <div className="space-y-2">
                {ble.status !== 'connected' ? (
                  <>
                    <button onClick={ble.connect} className="btn-primary w-full py-2.5">
                      Connect Assault Bike
                    </button>
                    <p className="text-xs text-white/30">BLE connection required for data capture</p>
                  </>
                ) : (
                  <p className="text-sm text-green-400">Connected to {ble.deviceName}</p>
                )}
              </div>
            )}
            <button
              onClick={protocol.startProtocol}
              disabled={protocol.state.config?.dataSource === 'ble' && ble.status !== 'connected'}
              className="btn-primary w-full py-3 text-base disabled:opacity-50"
            >
              Start Protocol
            </button>
            {protocol.state.config?.dataSource === 'manual' && (
              <p className="text-xs text-amber-400/70">Manual entry mode — no BLE needed</p>
            )}
          </div>
        )}

        {/* COUNTDOWNS */}
        {(phase === 'COUNTDOWN_1' || phase === 'COUNTDOWN_2' || phase === 'COUNTDOWN_3') && (
          <div className="text-center space-y-4">
            <div className="text-lg font-heading uppercase tracking-wider text-white">
              Sprint {phase === 'COUNTDOWN_1' ? 1 : phase === 'COUNTDOWN_2' ? 2 : 3} — Get Ready!
            </div>
            <div className="text-8xl font-bold font-mono text-amber-400">
              {protocol.state.countdown}
            </div>
          </div>
        )}

        {/* SPRINTS */}
        {(phase === 'SPRINT_1' || phase === 'SPRINT_2' || phase === 'SPRINT_3') && (
          <MetabolicSprint
            sprintNum={phase === 'SPRINT_1' ? 1 : phase === 'SPRINT_2' ? 2 : 3}
            remaining={protocol.state.sprintRemaining}
            samples={currentSprintSamples}
            livePower={livePower}
          />
        )}

        {/* RESTS */}
        {phase === 'REST_1' && (
          <MetabolicRest
            restNum={1}
            remaining={protocol.state.restRemaining}
            total={protocol.state.restTotal}
            onSubmitLactate={protocol.submitLactate}
          />
        )}
        {phase === 'REST_2' && (
          <MetabolicRest
            restNum={2}
            remaining={protocol.state.restRemaining}
            total={protocol.state.restTotal}
            onSubmitLactate={protocol.submitLactate}
          />
        )}

        {/* MANUAL ENTRY */}
        {phase === 'SPRINT_ENTRY' && (
          <MetabolicSprintEntry onSubmit={protocol.submitManualEntry} />
        )}

        {/* POST TEST */}
        {phase === 'POST_TEST' && (
          <div className="text-center space-y-4 max-w-xs mx-auto">
            <h2 className="text-lg font-heading font-bold">Final Lactate Sample</h2>
            {protocol.state.postTestRemaining > 0 ? (
              <>
                <div className="text-4xl font-bold font-mono text-amber-400">
                  {Math.floor(protocol.state.postTestRemaining / 60)}:{(protocol.state.postTestRemaining % 60).toString().padStart(2, '0')}
                </div>
                <p className="text-sm text-white/50">Wait for countdown, then take final blood lactate measurement.</p>
              </>
            ) : (
              <PostTestLactateInput onSubmit={protocol.submitFinalLactate} />
            )}
          </div>
        )}

        {/* RESULTS */}
        {phase === 'RESULTS' && protocol.state.config && (
          <MetabolicResults
            bodyMassKg={protocol.state.config.bodyMassKg}
            restingLactate={protocol.state.config.restingLactate}
            laPeaks={[
              protocol.state.laPeak1 ?? 0,
              protocol.state.laPeak2 ?? 0,
              protocol.state.laPeak3 ?? 0,
            ]}
            dataSource={protocol.state.config.dataSource}
            sprint1Samples={protocol.state.sprint1Samples}
            sprint2Samples={protocol.state.sprint2Samples}
            sprint3Samples={protocol.state.sprint3Samples}
            athleteId={athleteId}
            onSaved={handleSaved}
            onReset={() => {
              protocol.reset();
            }}
          />
        )}
      </div>
    </div>
  );

  return createPortal(overlay, document.body);
}

// Small inline component for post-test lactate input
function PostTestLactateInput({ onSubmit }: { onSubmit: (value: number) => void }) {
  const handleSubmit = () => {
    const input = document.getElementById('postTestLactateInput') as HTMLInputElement;
    const val = parseFloat(input?.value ?? '');
    if (isNaN(val) || val < 0 || val > 30) return;
    onSubmit(val);
  };

  return (
    <div className="space-y-3">
      <p className="text-sm text-white/60">Take the final lactate measurement now.</p>
      <div>
        <label className="text-sm text-white/60 block mb-1">La Peak 3 (mM)</label>
        <input
          id="postTestLactateInput"
          type="number" min={0} max={30} step={0.1}
          autoFocus
          className="w-full px-3 py-2 bg-primary-dark border border-secondary-muted/50 rounded-lg text-white text-center text-lg"
        />
      </div>
      <button onClick={handleSubmit} className="btn-primary w-full py-2.5">
        Calculate Results
      </button>
    </div>
  );
}
