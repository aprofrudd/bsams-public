'use client';

/**
 * Big-target decimal keypad for lab stations.
 *
 * `NumberStepper` cannot be used for measurements: its plus/minus variant strips
 * non-digits (`replace(/\D/g, '')`), so 41.2 is impossible to type. This also
 * avoids the iPad soft keyboard entirely, which matters when an operator is
 * entering a number every few seconds with a boxer waiting.
 */

const KEYS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '.', '0', 'back'] as const;

interface NumericKeypadProps {
  value: string;
  onChange: (value: string) => void;
  /** Digits allowed after the decimal point. */
  maxDecimals?: number;
  maxIntegerDigits?: number;
  disabled?: boolean;
}

export function appendKey(
  current: string,
  key: string,
  opts?: { maxDecimals?: number; maxIntegerDigits?: number }
): string {
  const maxDecimals = opts?.maxDecimals ?? 2;
  const maxIntegerDigits = opts?.maxIntegerDigits ?? 4;

  if (key === 'back') return current.slice(0, -1);
  if (key === 'clear') return '';

  if (key === '.') {
    if (current.includes('.')) return current;
    return current === '' ? '0.' : `${current}.`;
  }

  const [whole = '', decimals] = current.split('.');
  if (decimals === undefined) {
    if (whole.length >= maxIntegerDigits) return current;
    // Avoid a leading zero turning into "05"
    if (whole === '0') return key;
    return `${current}${key}`;
  }
  if (decimals.length >= maxDecimals) return current;
  return `${current}${key}`;
}

export function NumericKeypad({
  value,
  onChange,
  maxDecimals = 2,
  maxIntegerDigits = 4,
  disabled = false,
}: NumericKeypadProps) {
  const press = (key: string) => {
    onChange(appendKey(value, key, { maxDecimals, maxIntegerDigits }));
  };

  return (
    <div className="grid grid-cols-3 gap-2">
      {KEYS.map((key) => (
        <button
          key={key}
          type="button"
          disabled={disabled}
          onClick={() => press(key)}
          aria-label={key === 'back' ? 'Backspace' : key}
          className="min-h-[64px] rounded-xl bg-secondary-muted/25 text-2xl font-semibold text-white transition-all active:scale-[0.97] active:bg-secondary-muted/50 disabled:opacity-40"
        >
          {key === 'back' ? '⌫' : key}
        </button>
      ))}
      <button
        type="button"
        disabled={disabled}
        onClick={() => onChange('')}
        className="col-span-3 min-h-[52px] rounded-xl bg-secondary-muted/15 text-lg font-medium text-white/60 transition-all active:scale-[0.99] disabled:opacity-40"
      >
        Clear
      </button>
    </div>
  );
}
