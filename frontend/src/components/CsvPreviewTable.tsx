'use client';

import { getMetricLabel } from '@/lib/metricRegistry';

interface PreviewEvent {
  event_date: string;
  metrics: Record<string, string | number | undefined>;
  athlete_name?: string;
}

interface CsvPreviewTableProps {
  events: PreviewEvent[];
}

export function CsvPreviewTable({ events }: CsvPreviewTableProps) {
  if (events.length === 0) return null;

  const hasAthleteName = events.some((e) => e.athlete_name);

  // Collect all metric keys (excluding test_type)
  const metricKeys: string[] = [];
  const seen = new Set<string>();
  events.forEach((e) => {
    Object.keys(e.metrics).forEach((k) => {
      if (k !== 'test_type' && !seen.has(k)) {
        seen.add(k);
        metricKeys.push(k);
      }
    });
  });

  const formatValue = (val: string | number | undefined) => {
    if (val === undefined || val === null) return '-';
    if (typeof val === 'number') return val % 1 === 0 ? val.toString() : val.toFixed(1);
    return val;
  };

  return (
    <>
      {/* Mobile card list */}
      <div className="sm:hidden space-y-2">
        {events.map((event, i) => (
          <div key={i} className="bg-[#07083D] border border-[#2D5585] rounded-lg mb-2 p-3">
            <div className="flex items-baseline justify-between">
              <span className="text-white text-sm font-medium">{event.event_date}</span>
              {hasAthleteName && (
                <span className="text-white/60 text-xs ml-2">{event.athlete_name || '-'}</span>
              )}
            </div>
            <div className="mt-2 space-y-1">
              {metricKeys.map((key) => (
                <div key={key} className="flex justify-between text-xs">
                  <span className="text-white/40">{getMetricLabel(key)}</span>
                  <span className="text-white/80">{formatValue(event.metrics[key])}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Desktop table */}
      <div className="-mx-4 sm:mx-0 hidden sm:block overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-secondary-muted">
              <th className="text-left text-white/60 font-medium py-2 px-3">Date</th>
              {hasAthleteName && (
                <th className="text-left text-white/60 font-medium py-2 px-3">Athlete</th>
              )}
              {metricKeys.map((key) => (
                <th key={key} className="text-right text-white/60 font-medium py-2 px-3">
                  {getMetricLabel(key)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {events.map((event, i) => (
              <tr key={i} className="border-b border-secondary-muted/50 hover:bg-secondary-muted/20">
                <td className="py-2 px-3 text-white/80">{event.event_date}</td>
                {hasAthleteName && (
                  <td className="py-2 px-3 text-white/80">{event.athlete_name || '-'}</td>
                )}
                {metricKeys.map((key) => (
                  <td key={key} className="py-2 px-3 text-right text-white/80">
                    {formatValue(event.metrics[key])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
