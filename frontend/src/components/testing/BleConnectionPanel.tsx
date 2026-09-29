'use client';

import type { BleConnectionStatus } from '@/lib/hooks/useBleConnection';

interface BleConnectionPanelProps {
  status: BleConnectionStatus;
  deviceName: string | null;
  error: string | null;
  onConnect: () => void;
  onDisconnect: () => void;
}

const STATUS_CONFIG: Record<BleConnectionStatus, { label: string; color: string; dot: string }> = {
  disconnected: { label: 'Not Connected', color: 'text-white/40', dot: 'bg-white/20' },
  connecting: { label: 'Connecting...', color: 'text-amber-400', dot: 'bg-amber-400 animate-pulse' },
  connected: { label: 'Connected', color: 'text-green-400', dot: 'bg-green-400' },
};

export function BleConnectionPanel({
  status,
  deviceName,
  error,
  onConnect,
  onDisconnect,
}: BleConnectionPanelProps) {
  const config = STATUS_CONFIG[status];

  return (
    <div className="border border-secondary-muted/50 rounded-lg p-3 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${config.dot}`} />
          <span className={`text-sm font-medium ${config.color}`}>
            {config.label}
          </span>
          {deviceName && status === 'connected' && (
            <span className="text-xs text-white/30">({deviceName})</span>
          )}
        </div>
        {status === 'connected' ? (
          <button
            onClick={onDisconnect}
            className="text-sm px-3 py-1.5 rounded bg-secondary-muted/50 text-white/60 hover:text-white hover:bg-secondary-muted/70 transition-colors min-h-[36px]"
          >
            Disconnect
          </button>
        ) : (
          <button
            onClick={onConnect}
            disabled={status === 'connecting'}
            className="btn-primary text-sm px-4 py-1.5 min-h-[36px] disabled:opacity-50"
          >
            {status === 'connecting' ? 'Connecting...' : 'Connect Bike'}
          </button>
        )}
      </div>
      {error && (
        <p className="text-xs text-red-400">{error}</p>
      )}
    </div>
  );
}
