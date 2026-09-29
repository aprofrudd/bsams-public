/**
 * FTMS (Fitness Machine Service) Indoor Bike Data parser.
 * Service UUID: 0x1826, Characteristic UUID: 0x2AD2
 *
 * CRITICAL: Bit 0 is INVERTED — speed present when bit 0 = 0
 */

export interface FtmsData {
  instantSpeed?: number;      // km/h (uint16 * 0.01)
  averageSpeed?: number;      // km/h
  instantCadence?: number;    // rpm (uint16 * 0.5)
  averageCadence?: number;    // rpm
  totalDistance?: number;      // m (uint24)
  resistanceLevel?: number;   // sint16
  instantPower?: number;      // W (sint16)
  averagePower?: number;      // W
  totalEnergy?: number;       // kcal (uint16)
  energyPerHour?: number;     // kcal
  energyPerMinute?: number;   // kcal
  heartRate?: number;         // bpm
  metabolicEquivalent?: number;
  elapsedTime?: number;       // s
  remainingTime?: number;     // s
}

export const FTMS_SERVICE_UUID = 0x1826;
export const INDOOR_BIKE_DATA_UUID = 0x2AD2;

export function parseFtmsIndoorBikeData(dataView: DataView): FtmsData {
  const flags = dataView.getUint16(0, true);
  let offset = 2;
  const result: FtmsData = {};

  const readUint16 = (): number => { const v = dataView.getUint16(offset, true); offset += 2; return v; };
  const readSint16 = (): number => { const v = dataView.getInt16(offset, true); offset += 2; return v; };
  const readUint8 = (): number => { const v = dataView.getUint8(offset); offset += 1; return v; };
  const readUint24 = (): number => {
    const b0 = dataView.getUint8(offset);
    const b1 = dataView.getUint8(offset + 1);
    const b2 = dataView.getUint8(offset + 2);
    offset += 3;
    return b0 | (b1 << 8) | (b2 << 16);
  };

  // Bit 0: Instantaneous Speed — present when bit is 0 (INVERTED!)
  if (!(flags & 0x0001)) result.instantSpeed = readUint16() * 0.01;
  // Bit 1: Average Speed
  if (flags & 0x0002) result.averageSpeed = readUint16() * 0.01;
  // Bit 2: Instantaneous Cadence
  if (flags & 0x0004) result.instantCadence = readUint16() * 0.5;
  // Bit 3: Average Cadence
  if (flags & 0x0008) result.averageCadence = readUint16() * 0.5;
  // Bit 4: Total Distance (uint24)
  if (flags & 0x0010) result.totalDistance = readUint24();
  // Bit 5: Resistance Level
  if (flags & 0x0020) result.resistanceLevel = readSint16();
  // Bit 6: Instantaneous Power
  if (flags & 0x0040) result.instantPower = readSint16();
  // Bit 7: Average Power
  if (flags & 0x0080) result.averagePower = readSint16();
  // Bit 8: Expended Energy (uint16 + uint16 + uint8)
  if (flags & 0x0100) {
    result.totalEnergy = readUint16();
    result.energyPerHour = readUint16();
    result.energyPerMinute = readUint8();
  }
  // Bit 9: Heart Rate
  if (flags & 0x0200) result.heartRate = readUint8();
  // Bit 10: Metabolic Equivalent
  if (flags & 0x0400) result.metabolicEquivalent = readUint8() * 0.1;
  // Bit 11: Elapsed Time
  if (flags & 0x0800) result.elapsedTime = readUint16();
  // Bit 12: Remaining Time
  if (flags & 0x1000) result.remainingTime = readUint16();

  return result;
}
