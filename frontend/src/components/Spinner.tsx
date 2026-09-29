'use client';

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  message?: string;
}

const sizeClasses = {
  sm: 'w-4 h-4 border-2',
  md: 'w-6 h-6 border-2',
  lg: 'w-8 h-8 border-2',
};

export function Spinner({ size = 'md', message }: SpinnerProps) {
  return (
    <div className="text-center py-4">
      <div
        className={`inline-block ${sizeClasses[size]} border-accent border-t-transparent rounded-full animate-spin`}
      />
      {message && <p className="mt-2 text-white/60 text-sm">{message}</p>}
    </div>
  );
}
