'use client';

import { useState, useEffect, useCallback } from 'react';
import { airBikeApi } from '@/lib/api';
import { AirBikeTestForm } from './AirBikeTestForm';
import { AirBikeChart } from './AirBikeChart';
import { BleRecordingsTab } from './BleRecordingsTab';
import type { AirBikeTestListItem, AirBikeTest, AirBikeSprint } from '@/lib/types';
import { sprintMidPower, sprintMaxPower, sprintMidSeconds } from '@/lib/airBikeSplits';

type AirBikeSubTab = 'sprint-tests' | 'ble-recordings';

interface AirBikeViewProps {
  athleteId: string;
  athleteWeight: number | null;
  readOnly?: boolean;
}

function formatPower(value: number): string {
  return `${Math.round(value)}`;
}

function pctDiff(a: number, b: number): string {
  if (a === 0) return '0.0';
  return (((b - a) / a) * 100).toFixed(1);
}

function DecayAnalysis({
  sprints,
  bodyMassKg,
}: {
  sprints: AirBikeSprint[];
  bodyMassKg: number;
}) {
  const sprint1 = sprints.find((s) => s.sprint_number === 1);
  const sprint2 = sprints.find((s) => s.sprint_number === 2);
  if (!sprint1) return null;

  const s1Max = sprintMaxPower(sprint1);

  // Mid split is 14s or 17s depending on the protocol this test used
  const midSeconds = sprintMidSeconds(sprint1);
  const midLabel = `${midSeconds}s`;

  // Within-sprint decay (relative to own 7s)
  function withinSprintDecay(sprint: AirBikeSprint) {
    const mid = sprintMidPower(sprint);
    return {
      toMid: mid != null ? pctDiff(sprint.power_7s, mid) : null,
      to27: pctDiff(sprint.power_7s, sprint.power_27s),
      midTo27: mid != null ? pctDiff(mid, sprint.power_27s) : null,
    };
  }

  const s1Decay = withinSprintDecay(sprint1);

  // Between-sprint comparisons (Sprint 2 vs Sprint 1 at each time point)
  const s1Mid = sprintMidPower(sprint1);
  const s2Mid = sprint2 ? sprintMidPower(sprint2) : null;
  const betweenSprint = sprint2
    ? {
        at7s: pctDiff(sprint1.power_7s, sprint2.power_7s),
        atMid: s1Mid != null && s2Mid != null ? pctDiff(s1Mid, s2Mid) : null,
        at27s: pctDiff(sprint1.power_27s, sprint2.power_27s),
        peak: pctDiff(s1Max, sprintMaxPower(sprint2)),
      }
    : null;

  const s2Decay = sprint2 ? withinSprintDecay(sprint2) : null;

  return (
    <div className="border border-secondary-muted/50 rounded-lg p-3 space-y-3">
      <div className="text-sm font-heading uppercase tracking-wider text-accent">
        Decay Analysis
      </div>

      {/* Within-sprint decay */}
      <div className="space-y-2">
        <div className="text-xs text-white/40 font-medium">Within-Sprint Decay</div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-white/30">
                <th className="text-left py-1 pr-3"></th>
                <th className="text-center py-1 px-2">7s → {midLabel}</th>
                <th className="text-center py-1 px-2">{midLabel} → 27s</th>
                <th className="text-center py-1 px-2">7s → 27s</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t border-secondary-muted/20">
                <td className="py-1.5 pr-3 text-white/60">Sprint 1</td>
                <td className="py-1.5 px-2 text-center text-white/80">{s1Decay.toMid ?? '—'}%</td>
                <td className="py-1.5 px-2 text-center text-white/80">{s1Decay.midTo27 ?? '—'}%</td>
                <td className="py-1.5 px-2 text-center text-white font-medium">{s1Decay.to27}%</td>
              </tr>
              {s2Decay && (
                <tr className="border-t border-secondary-muted/20">
                  <td className="py-1.5 pr-3 text-white/60">Sprint 2</td>
                  <td className="py-1.5 px-2 text-center text-white/80">{s2Decay.toMid ?? '—'}%</td>
                  <td className="py-1.5 px-2 text-center text-white/80">{s2Decay.midTo27 ?? '—'}%</td>
                  <td className="py-1.5 px-2 text-center text-white font-medium">{s2Decay.to27}%</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Between-sprint comparison */}
      {betweenSprint && (
        <div className="space-y-2">
          <div className="text-xs text-white/40 font-medium">Sprint 2 vs Sprint 1</div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-white/30">
                  <th className="text-center py-1 px-2">7s</th>
                  <th className="text-center py-1 px-2">{midLabel}</th>
                  <th className="text-center py-1 px-2">27s</th>
                  <th className="text-center py-1 px-2 bg-accent/5">Peak</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-t border-secondary-muted/20">
                  <td className="py-1.5 px-2 text-center text-white/80">{betweenSprint.at7s}%</td>
                  <td className="py-1.5 px-2 text-center text-white/80">{betweenSprint.atMid ?? '—'}%</td>
                  <td className="py-1.5 px-2 text-center text-white/80">{betweenSprint.at27s}%</td>
                  <td className="py-1.5 px-2 text-center text-white font-medium bg-accent/5">{betweenSprint.peak}%</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function SprintResultsTable({
  sprints,
  bodyMassKg,
}: {
  sprints: AirBikeSprint[];
  bodyMassKg: number;
}) {
  const sprint1 = sprints.find((s) => s.sprint_number === 1);
  const sprint2 = sprints.find((s) => s.sprint_number === 2);

  if (!sprint1) return null;

  const midLabel = `${sprintMidSeconds(sprint1)}s`;

  function getSprintMax(sprint: AirBikeSprint): number {
    return sprintMaxPower(sprint);
  }

  // Sprint 1 peak is the reference for all % calculations
  const s1Peak = getSprintMax(sprint1);

  function renderCell(
    power: number,
    isMaxCell: boolean,
  ) {
    const wkg = bodyMassKg > 0 ? (power / bodyMassKg).toFixed(2) : null;
    const pctOfS1Peak = ((power / s1Peak) * 100).toFixed(1);

    return (
      <td
        className={`py-2 px-2 text-center ${
          isMaxCell ? 'bg-accent/10 text-accent font-semibold' : 'text-white'
        }`}
      >
        <div>{formatPower(power)} W</div>
        {wkg && <div className="text-xs text-white/40">{wkg} W/kg</div>}
        <div className="text-xs text-white/40">({pctOfS1Peak}%)</div>
      </td>
    );
  }

  function renderMaxCell(sprint: AirBikeSprint) {
    const maxP = getSprintMax(sprint);
    const wkg = bodyMassKg > 0 ? (maxP / bodyMassKg).toFixed(2) : null;
    const pctOfS1Peak = ((maxP / s1Peak) * 100).toFixed(1);

    return (
      <td className="py-2 px-2 text-center bg-accent/10 text-accent font-semibold">
        <div>{formatPower(maxP)} W</div>
        {wkg && <div className="text-xs text-white/40">{wkg} W/kg</div>}
        {sprint.sprint_number === 2 && (
          <div className="text-xs text-white/40">({pctOfS1Peak}%)</div>
        )}
      </td>
    );
  }

  function renderRow(sprint: AirBikeSprint, label: string) {
    const maxP = getSprintMax(sprint);
    const midPower = sprintMidPower(sprint);
    return (
      <tr className="border-t border-secondary-muted/30">
        <td className="py-2 px-2 text-sm text-white/60 font-medium">{label}</td>
        {renderCell(sprint.power_7s, sprint.power_7s === maxP)}
        {midPower != null && renderCell(midPower, midPower === maxP)}
        {renderCell(sprint.power_27s, sprint.power_27s === maxP)}
        {renderMaxCell(sprint)}
        <td className="py-2 px-2 text-center text-white/80 text-sm">
          {sprint.blood_lactate_mmol != null
            ? `${sprint.blood_lactate_mmol.toFixed(2)} mmol/L`
            : '-'}
        </td>
      </tr>
    );
  }

  return (
    <>
      {/* Desktop table */}
      <div className="hidden sm:block overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-white/40 text-xs">
              <th className="text-left py-1 px-2"></th>
              <th className="text-center py-1 px-2">7s Power</th>
              <th className="text-center py-1 px-2">{midLabel} Power</th>
              <th className="text-center py-1 px-2">27s Power</th>
              <th className="text-center py-1 px-2 bg-accent/5">Max Power</th>
              <th className="text-center py-1 px-2">Blood Lactate</th>
            </tr>
          </thead>
          <tbody>
            {renderRow(sprint1, 'Sprint 1')}
            {sprint2 && renderRow(sprint2, 'Sprint 2')}
          </tbody>
        </table>
        <p className="text-[10px] text-white/25 mt-1 text-right">% relative to Sprint 1 peak</p>
      </div>

      {/* Mobile stacked cards */}
      <div className="sm:hidden space-y-3">
        {[sprint1, sprint2].filter(Boolean).map((sprint) => {
          if (!sprint) return null;
          const maxP = getSprintMax(sprint);
          const label = sprint.sprint_number === 1 ? 'Sprint 1' : 'Sprint 2';
          return (
            <div
              key={sprint.id}
              className="border border-secondary-muted/50 rounded-lg p-3 space-y-2"
            >
              <div className="text-sm font-heading uppercase tracking-wider text-accent">
                {label}
              </div>
              <div className="grid grid-cols-3 gap-2 text-center text-sm">
                {(
                  [
                    { label: '7s', power: sprint.power_7s as number },
                    { label: `${sprintMidSeconds(sprint)}s`, power: sprintMidPower(sprint) },
                    { label: '27s', power: sprint.power_27s as number },
                  ].filter((d) => d.power != null) as { label: string; power: number }[]
                ).map(({ label: timeLabel, power }) => (
                  <div
                    key={timeLabel}
                    className={`rounded p-1.5 ${
                      power === maxP ? 'bg-accent/10' : ''
                    }`}
                  >
                    <div className="text-xs text-white/40">{timeLabel}</div>
                    <div className={power === maxP ? 'text-accent font-semibold' : 'text-white'}>
                      {formatPower(power)} W
                    </div>
                    {bodyMassKg > 0 && (
                      <div className="text-xs text-white/40">
                        {(power / bodyMassKg).toFixed(2)} W/kg
                      </div>
                    )}
                    <div className="text-xs text-white/30">
                      ({((power / s1Peak) * 100).toFixed(1)}%)
                    </div>
                  </div>
                ))}
              </div>
              <div className="flex justify-between text-xs text-white/40">
                <span>
                  Max: <span className="text-accent font-semibold">{formatPower(maxP)} W</span>
                </span>
                {sprint.blood_lactate_mmol != null && (
                  <span>Lactate: {sprint.blood_lactate_mmol.toFixed(2)} mmol/L</span>
                )}
              </div>
            </div>
          );
        })}
        <p className="text-[10px] text-white/25">% relative to Sprint 1 peak</p>
      </div>

      {/* Decay Analysis */}
      <DecayAnalysis sprints={sprints} bodyMassKg={bodyMassKg} />
    </>
  );
}

export function AirBikeView({ athleteId, readOnly }: AirBikeViewProps) {
  const [subTab, setSubTab] = useState<AirBikeSubTab>('sprint-tests');

  const SUB_TABS: { key: AirBikeSubTab; label: string }[] = [
    { key: 'sprint-tests', label: 'Sprint Tests' },
    { key: 'ble-recordings', label: 'BLE Recordings' },
  ];

  return (
    <div className="space-y-4">
      {/* Sub-tab selector */}
      <div className="flex gap-1 border-b border-secondary-muted/30 pb-0">
        {SUB_TABS.map(tab => (
          <button
            key={tab.key}
            onClick={() => setSubTab(tab.key)}
            className={`px-3 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              subTab === tab.key
                ? 'border-accent text-accent'
                : 'border-transparent text-white/40 hover:text-white/60'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Sub-tab content */}
      {subTab === 'sprint-tests' && (
        <SprintTestsContent athleteId={athleteId} readOnly={readOnly} />
      )}
      {subTab === 'ble-recordings' && (
        <BleRecordingsTab athleteId={athleteId} readOnly={readOnly} />
      )}
    </div>
  );
}

function SprintTestsContent({ athleteId, readOnly }: { athleteId: string; readOnly?: boolean }) {
  const [tests, setTests] = useState<AirBikeTestListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editTest, setEditTest] = useState<AirBikeTest | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [expandedTest, setExpandedTest] = useState<AirBikeTest | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const loadTests = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await airBikeApi.listTests(athleteId);
      setTests(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tests');
    } finally {
      setLoading(false);
    }
  }, [athleteId]);

  useEffect(() => {
    loadTests();
  }, [loadTests]);

  async function handleExpand(testId: string) {
    if (expandedId === testId) {
      setExpandedId(null);
      setExpandedTest(null);
      return;
    }
    try {
      const full = await airBikeApi.getTest(testId);
      setExpandedTest(full);
      setExpandedId(testId);
    } catch {
      // Silently fail expand
    }
  }

  async function handleEdit(testId: string) {
    try {
      const full = await airBikeApi.getTest(testId);
      setEditTest(full);
      setShowForm(true);
    } catch {
      // Silently fail
    }
  }

  async function handleDelete(testId: string) {
    if (!confirm('Delete this air bike test?')) return;
    setDeleting(testId);
    try {
      await airBikeApi.deleteTest(testId);
      setTests((prev) => prev.filter((t) => t.id !== testId));
      if (expandedId === testId) {
        setExpandedId(null);
        setExpandedTest(null);
      }
    } catch {
      // Silently fail delete
    } finally {
      setDeleting(null);
    }
  }

  function handleSaved() {
    setShowForm(false);
    setEditTest(null);
    loadTests();
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with New Test button */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-white/40">
          {tests.length} test{tests.length !== 1 ? 's' : ''}
        </p>
        {!readOnly && (
          <button
            onClick={() => {
              setEditTest(null);
              setShowForm(true);
            }}
            className="btn-primary text-sm px-4 py-1.5"
          >
            + New Test
          </button>
        )}
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      {tests.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-white/40 text-sm mb-3">No air bike tests yet</p>
          {!readOnly && (
            <button
              onClick={() => setShowForm(true)}
              className="btn-primary text-sm px-4 py-1.5"
            >
              Create First Test
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          {tests.map((t) => (
            <div
              key={t.id}
              className="border border-secondary-muted/50 rounded-lg overflow-hidden"
            >
              {/* Test Summary Row */}
              <div
                className="flex items-center justify-between px-4 py-3 min-h-[44px] cursor-pointer hover:bg-secondary-muted/20 active:bg-secondary-muted/30 transition-colors"
                onClick={() => handleExpand(t.id)}
              >
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="text-sm text-white/80">
                    {new Date(t.test_date).toLocaleDateString('en-GB', {
                      day: 'numeric',
                      month: 'short',
                      year: 'numeric',
                    })}
                  </span>
                  <span className="inline-block px-1.5 py-0.5 rounded text-xs font-medium bg-blue-500/20 text-blue-400">
                    {t.body_mass_kg} kg
                  </span>
                  {t.max_power_w != null && (
                    <span className="text-sm font-semibold text-white">
                      Max: {Math.round(t.max_power_w)} W
                    </span>
                  )}
                  <span className="text-xs text-white/30">
                    {t.sprint_count} sprint{t.sprint_count !== 1 ? 's' : ''}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {!readOnly && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleEdit(t.id);
                      }}
                      className="text-white/30 hover:text-accent active:text-accent/70 p-2 min-h-[44px] min-w-[44px] flex items-center justify-center transition-colors"
                      title="Edit"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 16 16"
                        fill="currentColor"
                        className="w-4 h-4"
                      >
                        <path d="M13.488 2.513a1.75 1.75 0 0 0-2.475 0L6.75 6.774a2.75 2.75 0 0 0-.596.892l-.848 2.047a.75.75 0 0 0 .98.98l2.047-.848a2.75 2.75 0 0 0 .892-.596l4.261-4.262a1.75 1.75 0 0 0 0-2.474Z" />
                        <path d="M4.75 3.5c-.69 0-1.25.56-1.25 1.25v6.5c0 .69.56 1.25 1.25 1.25h6.5c.69 0 1.25-.56 1.25-1.25V9A.75.75 0 0 1 14 9v2.25A2.75 2.75 0 0 1 11.25 14h-6.5A2.75 2.75 0 0 1 2 11.25v-6.5A2.75 2.75 0 0 1 4.75 2H7a.75.75 0 0 1 0 1.5H4.75Z" />
                      </svg>
                    </button>
                  )}
                  {!readOnly && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(t.id);
                      }}
                      disabled={deleting === t.id}
                      className="text-white/30 hover:text-red-400 active:text-red-300 p-2 min-h-[44px] min-w-[44px] flex items-center justify-center transition-colors disabled:opacity-50"
                      title="Delete"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 16 16"
                        fill="currentColor"
                        className="w-4 h-4"
                      >
                        <path
                          fillRule="evenodd"
                          d="M5 3.25V4H2.75a.75.75 0 0 0 0 1.5h.3l.815 8.15A1.5 1.5 0 0 0 5.357 15h5.285a1.5 1.5 0 0 0 1.493-1.35l.815-8.15h.3a.75.75 0 0 0 0-1.5H11v-.75A2.25 2.25 0 0 0 8.75 1h-1.5A2.25 2.25 0 0 0 5 3.25Zm2.25-.75a.75.75 0 0 0-.75.75V4h3v-.75a.75.75 0 0 0-.75-.75h-1.5ZM6.05 6a.75.75 0 0 1 .787.713l.275 5.5a.75.75 0 0 1-1.498.075l-.275-5.5A.75.75 0 0 1 6.05 6Zm3.9 0a.75.75 0 0 1 .712.787l-.275 5.5a.75.75 0 0 1-1.498-.075l.275-5.5a.75.75 0 0 1 .786-.711Z"
                          clipRule="evenodd"
                        />
                      </svg>
                    </button>
                  )}
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 16 16"
                    fill="currentColor"
                    className={`w-4 h-4 text-white/30 transition-transform ${
                      expandedId === t.id ? 'rotate-180' : ''
                    }`}
                  >
                    <path
                      fillRule="evenodd"
                      d="M4.22 6.22a.75.75 0 0 1 1.06 0L8 8.94l2.72-2.72a.75.75 0 1 1 1.06 1.06l-3.25 3.25a.75.75 0 0 1-1.06 0L4.22 7.28a.75.75 0 0 1 0-1.06Z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
              </div>

              {/* Expanded Detail */}
              {expandedId === t.id && expandedTest && (
                <div className="border-t border-secondary-muted/50 px-4 py-3 space-y-4 bg-primary-dark/30">
                  {/* Results Table */}
                  <SprintResultsTable
                    sprints={expandedTest.sprints}
                    bodyMassKg={expandedTest.body_mass_kg}
                  />

                  {/* Power Decay Chart */}
                  <AirBikeChart test={expandedTest} />

                  {/* Notes */}
                  {expandedTest.notes && (
                    <p className="text-xs text-white/40">{expandedTest.notes}</p>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Form Modal */}
      {showForm && (
        <AirBikeTestForm
          athleteId={athleteId}
          existingTest={editTest}
          onClose={() => {
            setShowForm(false);
            setEditTest(null);
          }}
          onSaved={handleSaved}
        />
      )}
    </div>
  );
}
