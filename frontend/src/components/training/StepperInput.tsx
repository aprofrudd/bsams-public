'use client';

interface StepperInputProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  label?: string;
}

export function StepperInput({
  value,
  onChange,
  min = 1,
  max = 99,
  label,
}: StepperInputProps) {
  return (
    <div className="flex items-center gap-2">
      {label && <span className="text-xs text-white/60 mr-1">{label}</span>}
      <button
        type="button"
        onClick={() => onChange(Math.max(min, value - 1))}
        disabled={value <= min}
        className="w-11 h-11 min-w-[44px] min-h-[44px] flex items-center justify-center rounded bg-secondary-muted/30 text-white font-bold text-lg hover:bg-secondary-muted/50 active:scale-[0.97] transition-all disabled:opacity-30 disabled:cursor-not-allowed"
      >
        -
      </button>
      <span className="w-10 text-center text-sm font-medium tabular-nums">{value}</span>
      <button
        type="button"
        onClick={() => onChange(Math.min(max, value + 1))}
        disabled={value >= max}
        className="w-11 h-11 min-w-[44px] min-h-[44px] flex items-center justify-center rounded bg-secondary-muted/30 text-white font-bold text-lg hover:bg-secondary-muted/50 active:scale-[0.97] transition-all disabled:opacity-30 disabled:cursor-not-allowed"
      >
        +
      </button>
    </div>
  );
}
