'use client';

import { useState, useRef, useEffect } from 'react';

interface NumberStepperProps {
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step?: number;
  label?: string;
  /** 'segments' for small ranges (1-10), 'plusminus' for large ranges (direct text input) */
  variant?: 'segments' | 'plusminus';
}

export function NumberStepper({
  value,
  onChange,
  min,
  max,
  step = 1,
  label,
  variant = 'segments',
}: NumberStepperProps) {
  if (variant === 'plusminus') {
    return (
      <PlusMinusStepper
        value={value}
        onChange={onChange}
        min={min}
        max={max}
        step={step}
        label={label}
      />
    );
  }

  return (
    <SegmentStepper
      value={value}
      onChange={onChange}
      min={min}
      max={max}
      step={step}
      label={label}
    />
  );
}

function SegmentStepper({
  value,
  onChange,
  min,
  max,
  step,
}: Omit<NumberStepperProps, 'variant'>) {
  const segments: number[] = [];
  for (let i = min; i <= max; i += step || 1) {
    segments.push(i);
  }

  return (
    <div className="flex gap-1 flex-wrap">
      {segments.map((n) => (
        <button
          key={n}
          type="button"
          onClick={() => onChange(n)}
          className={`min-w-[32px] min-h-[44px] px-2 py-1 rounded-md text-sm font-medium transition-all active:scale-[0.95] ${
            value === n
              ? 'bg-accent text-[#090A3D] shadow-sm'
              : 'bg-secondary-muted/20 text-white/60 hover:bg-secondary-muted/40 active:bg-secondary-muted/40'
          }`}
        >
          {n}
        </button>
      ))}
    </div>
  );
}

function PlusMinusStepper({
  value,
  onChange,
  min,
  max,
}: Omit<NumberStepperProps, 'variant'>) {
  const [displayValue, setDisplayValue] = useState(value ? String(value) : '');
  const lastEmittedRef = useRef(value);

  useEffect(() => {
    if (value !== lastEmittedRef.current) {
      lastEmittedRef.current = value;
      setDisplayValue(value ? String(value) : '');
    }
  }, [value]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value.replace(/\D/g, '');
    if (raw === '') {
      setDisplayValue('');
      lastEmittedRef.current = 0;
      onChange(0);
      return;
    }
    let num = parseInt(raw, 10);
    if (num > max) num = max;
    setDisplayValue(String(num));
    lastEmittedRef.current = num;
    onChange(num);
  };

  const handleBlur = () => {
    const num = parseInt(displayValue, 10);
    if (!displayValue || isNaN(num) || num < min) {
      const clamped = min;
      setDisplayValue(String(clamped));
      lastEmittedRef.current = clamped;
      onChange(clamped);
    }
  };

  return (
    <input
      type="text"
      inputMode="numeric"
      pattern="[0-9]*"
      value={displayValue}
      onChange={handleChange}
      onBlur={handleBlur}
      placeholder={`${min}-${max}`}
      aria-label="Duration in minutes"
      className="input w-24 text-center text-lg font-medium tabular-nums"
    />
  );
}
