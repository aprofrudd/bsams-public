'use client';

import { useState, useCallback } from 'react';
import { BleCompatibilityGate } from './BleCompatibilityGate';
import { BleConnectionPanel } from './BleConnectionPanel';
import { BleLiveDataGrid } from './BleLiveDataGrid';
import { BleStandardRecorder } from './BleStandardRecorder';
import { BleRecordingsList } from './BleRecordingsList';
import { useBleConnection } from '@/lib/hooks/useBleConnection';
import { useBleRecorder } from '@/lib/hooks/useBleRecorder';

interface BleRecordingsTabProps {
  athleteId: string;
  readOnly?: boolean;
}

export function BleRecordingsTab({ athleteId, readOnly }: BleRecordingsTabProps) {
  const [refreshKey, setRefreshKey] = useState(0);

  const recorder = useBleRecorder();
  const ble = useBleConnection(recorder.handleData);

  const handleSaved = useCallback(() => {
    setRefreshKey(k => k + 1);
  }, []);

  return (
    <BleCompatibilityGate>
      <div className="space-y-4">
        {/* Connection */}
        <BleConnectionPanel
          status={ble.status}
          deviceName={ble.deviceName}
          error={ble.error}
          onConnect={ble.connect}
          onDisconnect={ble.disconnect}
        />

        {/* Live data grid */}
        {ble.status === 'connected' && (
          <BleLiveDataGrid data={ble.liveData} />
        )}

        {/* Recorder */}
        {!readOnly && (
          <BleStandardRecorder
            athleteId={athleteId}
            recorderState={recorder.state}
            samples={recorder.samples}
            countdown={recorder.countdown}
            elapsed={recorder.elapsed}
            remaining={recorder.remaining}
            onStart={recorder.start}
            onStop={recorder.stop}
            onReset={recorder.reset}
            onSaved={handleSaved}
            isConnected={ble.status === 'connected'}
          />
        )}

        {/* Saved recordings */}
        <div className="border-t border-secondary-muted/30 pt-4">
          <div className="text-sm font-heading uppercase tracking-wider text-accent mb-3">
            Saved Recordings
          </div>
          <BleRecordingsList
            athleteId={athleteId}
            refreshKey={refreshKey}
            readOnly={readOnly}
          />
        </div>
      </div>
    </BleCompatibilityGate>
  );
}
