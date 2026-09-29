'use client';

interface BleCompatibilityGateProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export function BleCompatibilityGate({ children, fallback }: BleCompatibilityGateProps) {
  // Check for Web Bluetooth API availability
  // Use truthy check, not 'bluetooth' in navigator (which is true in Firefox but non-functional)
  const isSupported = typeof window !== 'undefined' && !!navigator.bluetooth;

  if (!isSupported) {
    if (fallback) return <>{fallback}</>;
    return (
      <div className="border border-amber-500/30 rounded-lg p-4 bg-amber-500/5">
        <div className="flex items-start gap-3">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 text-amber-400 mt-0.5 shrink-0">
            <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495ZM10 5a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 10 5Zm0 9a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z" clipRule="evenodd" />
          </svg>
          <div>
            <p className="text-sm text-amber-400 font-medium">Web Bluetooth Not Available</p>
            <p className="text-xs text-white/50 mt-1">
              BLE features require Chrome or Edge on desktop/Android. Firefox and Safari do not support Web Bluetooth.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
