'use client';

interface RpeSelectorProps {
  value: number;
  onChange: (value: number) => void;
}

const RPE_ZONES: Record<number, string> = {
  1: 'bg-green-500/20 text-green-400 border-green-500/30',
  2: 'bg-green-500/20 text-green-400 border-green-500/30',
  3: 'bg-green-500/20 text-green-400 border-green-500/30',
  4: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  5: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  6: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  7: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  8: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  9: 'bg-red-500/20 text-red-400 border-red-500/30',
  10: 'bg-red-500/20 text-red-400 border-red-500/30',
};

const RPE_ACTIVE: Record<number, string> = {
  1: 'bg-green-500 text-white border-green-500',
  2: 'bg-green-500 text-white border-green-500',
  3: 'bg-green-500 text-white border-green-500',
  4: 'bg-yellow-500 text-white border-yellow-500',
  5: 'bg-yellow-500 text-white border-yellow-500',
  6: 'bg-yellow-500 text-white border-yellow-500',
  7: 'bg-orange-500 text-white border-orange-500',
  8: 'bg-orange-500 text-white border-orange-500',
  9: 'bg-red-500 text-white border-red-500',
  10: 'bg-red-500 text-white border-red-500',
};

export function RpeSelector({ value, onChange }: RpeSelectorProps) {
  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => (
        <button
          key={n}
          type="button"
          onClick={() => onChange(n)}
          className={`flex-1 min-w-[28px] min-h-[44px] rounded-md text-sm font-bold border transition-all active:scale-[0.93] ${
            value === n ? RPE_ACTIVE[n] : RPE_ZONES[n]
          }`}
        >
          {n}
        </button>
      ))}
    </div>
  );
}
