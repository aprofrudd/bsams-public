'use client';

import { useState } from 'react';
import type { VbtAnalysis } from '@/lib/types';

interface VbtCalculatorProps {
  analysis: VbtAnalysis;
}

type CalcMode = 'velocity_to_load' | 'percent_to_velocity';

export function VbtCalculator({ analysis }: VbtCalculatorProps) {
  const [mode, setMode] = useState<CalcMode>('velocity_to_load');
  const [velocityInput, setVelocityInput] = useState('');
  const [percentInput, setPercentInput] = useState('');

  // Client-side calculation using regression coefficients
  function predictLoad(velocity: number): number | null {
    if (analysis.slope === 0) return null;
    const load = (velocity - analysis.intercept) / analysis.slope;
    return load > 0 ? Math.round(load * 10) / 10 : null;
  }

  function predictVelocity(loadKg: number): number {
    return Math.round((analysis.slope * loadKg + analysis.intercept) * 1000) / 1000;
  }

  const velocityVal = Number(velocityInput);
  const percentVal = Number(percentInput);

  // Mode A: Velocity → Load
  const predictedLoad =
    mode === 'velocity_to_load' && velocityInput && !isNaN(velocityVal) && velocityVal >= 0
      ? predictLoad(velocityVal)
      : null;

  const predictedPercent =
    predictedLoad != null && analysis.estimated_1rm_kg
      ? Math.round((predictedLoad / analysis.estimated_1rm_kg) * 1000) / 10
      : null;

  // Mode B: %1RM → Velocity
  const targetLoad =
    mode === 'percent_to_velocity' &&
    percentInput &&
    !isNaN(percentVal) &&
    percentVal > 0 &&
    percentVal <= 100 &&
    analysis.estimated_1rm_kg
      ? Math.round(analysis.estimated_1rm_kg * (percentVal / 100) * 10) / 10
      : null;

  const predictedVelocity = targetLoad != null ? predictVelocity(targetLoad) : null;

  return (
    <div className="space-y-3">
      <h4 className="text-xs font-heading uppercase tracking-wider text-white/40">
        Velocity Threshold Calculator
      </h4>

      {/* Mode Toggle */}
      <div className="flex bg-secondary-muted/30 rounded-lg p-0.5">
        <button
          type="button"
          onClick={() => setMode('velocity_to_load')}
          className={`flex-1 px-2 py-1.5 min-h-[44px] rounded-md text-xs font-medium transition-colors ${
            mode === 'velocity_to_load'
              ? 'bg-accent text-[#090A3D] active:bg-accent/80'
              : 'text-white/60 hover:text-white active:text-white/80'
          }`}
        >
          Velocity &rarr; Load
        </button>
        <button
          type="button"
          onClick={() => setMode('percent_to_velocity')}
          className={`flex-1 px-2 py-1.5 min-h-[44px] rounded-md text-xs font-medium transition-colors ${
            mode === 'percent_to_velocity'
              ? 'bg-accent text-[#090A3D] active:bg-accent/80'
              : 'text-white/60 hover:text-white active:text-white/80'
          }`}
        >
          %1RM &rarr; Velocity
        </button>
      </div>

      {mode === 'velocity_to_load' ? (
        <div className="space-y-2">
          <div>
            <label className="block text-xs text-white/40 mb-1">Target Velocity (m/s)</label>
            <input
              type="number"
              step="0.01"
              min="0"
              max="5"
              value={velocityInput}
              onChange={(e) => setVelocityInput(e.target.value)}
              className="input w-full text-sm"
              placeholder="e.g. 0.40"
            />
          </div>
          {predictedLoad != null && (
            <div className="bg-secondary-muted/20 rounded-lg p-3 text-center">
              <div className="text-xs text-white/40">Predicted Load</div>
              <div className="text-xl font-semibold text-white">
                {predictedLoad} <span className="text-sm text-white/40">kg</span>
              </div>
              {predictedPercent != null && (
                <div className="text-xs text-white/40 mt-1">
                  ≈ {predictedPercent}% 1RM
                </div>
              )}
            </div>
          )}
          {velocityInput && predictedLoad == null && !isNaN(velocityVal) && (
            <p className="text-xs text-white/30">No valid prediction for this velocity</p>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          {!analysis.estimated_1rm_kg ? (
            <p className="text-xs text-white/40">Cannot calculate: no valid 1RM estimate</p>
          ) : (
            <>
              <div>
                <label className="block text-xs text-white/40 mb-1">Target %1RM</label>
                <input
                  type="number"
                  step="1"
                  min="1"
                  max="100"
                  value={percentInput}
                  onChange={(e) => setPercentInput(e.target.value)}
                  className="input w-full text-sm"
                  placeholder="e.g. 85"
                />
              </div>
              {targetLoad != null && predictedVelocity != null && (
                <div className="bg-secondary-muted/20 rounded-lg p-3 text-center">
                  <div className="text-xs text-white/40">
                    Load at {percentVal}% 1RM = {targetLoad} kg
                  </div>
                  <div className="text-xl font-semibold text-white">
                    {predictedVelocity.toFixed(3)}{' '}
                    <span className="text-sm text-white/40">m/s</span>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
