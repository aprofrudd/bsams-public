import { useState, useCallback, useRef } from 'react';
import { parseFtmsIndoorBikeData, FTMS_SERVICE_UUID, INDOOR_BIKE_DATA_UUID } from '../bleProtocol';
import type { FtmsData } from '../bleProtocol';

export type BleConnectionStatus = 'disconnected' | 'connecting' | 'connected';

interface UseBleConnectionReturn {
  status: BleConnectionStatus;
  deviceName: string | null;
  liveData: FtmsData | null;
  connect: () => Promise<void>;
  disconnect: () => void;
  error: string | null;
}

export function useBleConnection(
  onData?: (data: FtmsData) => void
): UseBleConnectionReturn {
  const [status, setStatus] = useState<BleConnectionStatus>('disconnected');
  const [deviceName, setDeviceName] = useState<string | null>(null);
  const [liveData, setLiveData] = useState<FtmsData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const deviceRef = useRef<BluetoothDevice | null>(null);
  const charRef = useRef<BluetoothRemoteGATTCharacteristic | null>(null);
  const onDataRef = useRef(onData);
  onDataRef.current = onData;

  const handleNotification = useCallback((event: Event) => {
    const target = event.target as BluetoothRemoteGATTCharacteristic;
    if (!target.value) return;
    const parsed = parseFtmsIndoorBikeData(target.value);
    setLiveData(parsed);
    onDataRef.current?.(parsed);
  }, []);

  const onDisconnected = useCallback(() => {
    charRef.current = null;
    deviceRef.current = null;
    setStatus('disconnected');
    setDeviceName(null);
    setLiveData(null);
  }, []);

  const cleanup = useCallback(() => {
    if (charRef.current) {
      try {
        charRef.current.removeEventListener('characteristicvaluechanged', handleNotification);
        charRef.current.stopNotifications().catch(() => {});
      } catch { /* ignore */ }
      charRef.current = null;
    }
    if (deviceRef.current) {
      try {
        deviceRef.current.removeEventListener('gattserverdisconnected', onDisconnected);
        if (deviceRef.current.gatt?.connected) {
          deviceRef.current.gatt.disconnect();
        }
      } catch { /* ignore */ }
      deviceRef.current = null;
    }
  }, [handleNotification, onDisconnected]);

  const connect = useCallback(async () => {
    if (!navigator.bluetooth) {
      setError('Web Bluetooth not available');
      return;
    }

    setError(null);
    setStatus('connecting');

    try {
      const device = await navigator.bluetooth.requestDevice({
        filters: [{ services: [FTMS_SERVICE_UUID] }],
      });

      deviceRef.current = device;
      setDeviceName(device.name || 'Unknown device');
      device.addEventListener('gattserverdisconnected', onDisconnected);

      const server = await device.gatt!.connect();
      const service = await server.getPrimaryService(FTMS_SERVICE_UUID);
      const characteristic = await service.getCharacteristic(INDOOR_BIKE_DATA_UUID);

      await characteristic.startNotifications();
      characteristic.addEventListener('characteristicvaluechanged', handleNotification);
      charRef.current = characteristic;

      setStatus('connected');
    } catch (err) {
      cleanup();
      setStatus('disconnected');
      if (err instanceof Error) {
        if (err.name === 'NotFoundError') {
          setError('No device selected');
        } else if (err.name === 'SecurityError') {
          setError('Must be served over HTTPS or localhost');
        } else if (err.name === 'NetworkError') {
          setError('Connection failed — check device is on and in range');
        } else {
          setError(err.message);
        }
      }
    }
  }, [cleanup, handleNotification, onDisconnected]);

  const disconnect = useCallback(() => {
    cleanup();
    setStatus('disconnected');
    setDeviceName(null);
    setLiveData(null);
    setError(null);
  }, [cleanup]);

  return { status, deviceName, liveData, connect, disconnect, error };
}
