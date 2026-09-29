'use client';

import { useState, useEffect, useCallback } from 'react';
import { lactateApi } from '@/lib/api';
import { detectBreakpoints } from '@/lib/lactateAnalysis';
import { LactateTestForm } from './LactateTestForm';
import { LactateChart } from './LactateChart';
import { GasAnalysisUpload } from './GasAnalysisUpload';
import { ThresholdMetricsPanel } from './ThresholdMetricsPanel';
import { FatMaxSummary } from './FatMaxSummary';
import type { LactateTestListItem, LactateTest, GasAnalysisData } from '@/lib/types';

interface LactateProfilesViewProps {
  athleteId: string;
  readOnly?: boolean;
}

function TypeBadge({ testType }: { testType: 'running' | 'cycling' }) {
  const color =
    testType === 'running'
      ? 'bg-green-500/20 text-green-400'
      : 'bg-blue-500/20 text-blue-400';
  return (
    <span className={`inline-block px-1.5 py-0.5 rounded text-xs font-medium ${color}`}>
      {testType === 'running' ? 'Running' : 'Cycling'}
    </span>
  );
}

function CpetBadge() {
  return (
    <span className="inline-block px-1.5 py-0.5 rounded text-xs font-medium bg-purple-500/20 text-purple-400">
      CPET
    </span>
  );
}

export function LactateProfilesView({ athleteId, readOnly }: LactateProfilesViewProps) {
  const [tests, setTests] = useState<LactateTestListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editTest, setEditTest] = useState<LactateTest | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [expandedTest, setExpandedTest] = useState<LactateTest | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  // Gas analysis state
  const [gasAnalysis, setGasAnalysis] = useState<GasAnalysisData | null>(null);
  const [showGasUpload, setShowGasUpload] = useState(false);
  const [deletingGas, setDeletingGas] = useState(false);

  // Threshold editor state
  const [lt1Value, setLt1Value] = useState('');
  const [lt1Lactate, setLt1Lactate] = useState('');
  const [lt1Hr, setLt1Hr] = useState('');
  const [lt2Value, setLt2Value] = useState('');
  const [lt2Lactate, setLt2Lactate] = useState('');
  const [lt2Hr, setLt2Hr] = useState('');
  const [savingThresholds, setSavingThresholds] = useState(false);

  const loadTests = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await lactateApi.listTests(athleteId);
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

  function syncThresholdState(test: LactateTest) {
    setLt1Value(test.lt1_value != null ? String(test.lt1_value) : '');
    setLt1Lactate(test.lt1_lactate != null ? String(test.lt1_lactate) : '');
    setLt1Hr(test.lt1_hr != null ? String(test.lt1_hr) : '');
    setLt2Value(test.lt2_value != null ? String(test.lt2_value) : '');
    setLt2Lactate(test.lt2_lactate != null ? String(test.lt2_lactate) : '');
    setLt2Hr(test.lt2_hr != null ? String(test.lt2_hr) : '');
  }

  async function loadGasAnalysis(testId: string) {
    try {
      const data = await lactateApi.getGasAnalysis(testId);
      setGasAnalysis(data);
    } catch {
      setGasAnalysis(null);
    }
  }

  async function handleExpand(testId: string) {
    if (expandedId === testId) {
      setExpandedId(null);
      setExpandedTest(null);
      setGasAnalysis(null);
      return;
    }
    try {
      const full = await lactateApi.getTest(testId);
      setExpandedTest(full);
      setExpandedId(testId);
      syncThresholdState(full);
      if (full.has_gas_analysis) {
        loadGasAnalysis(testId);
      } else {
        setGasAnalysis(null);
      }
    } catch {
      // Silently fail expand
    }
  }

  async function handleEdit(testId: string) {
    try {
      const full = await lactateApi.getTest(testId);
      setEditTest(full);
      setShowForm(true);
    } catch {
      // Silently fail
    }
  }

  async function handleDelete(testId: string) {
    if (!confirm('Delete this lactate test?')) return;
    setDeleting(testId);
    try {
      await lactateApi.deleteTest(testId);
      setTests((prev) => prev.filter((t) => t.id !== testId));
      if (expandedId === testId) {
        setExpandedId(null);
        setExpandedTest(null);
        setGasAnalysis(null);
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

  function handleAutoDetect() {
    if (!expandedTest) return;
    const intensities: number[] = [];
    const lactates: number[] = [];
    for (const s of expandedTest.stages) {
      if (s.intensity_value != null && s.blood_lactate_mmol != null) {
        intensities.push(s.intensity_value);
        lactates.push(s.blood_lactate_mmol);
      }
    }
    const result = detectBreakpoints(intensities, lactates);
    if (result) {
      setLt1Value(String(result.lt1_x));
      setLt1Lactate(String(result.lt1_lactate));
      setLt2Value(String(result.lt2_x));
      setLt2Lactate(String(result.lt2_lactate));
    }
  }

  async function handleSaveThresholds() {
    if (!expandedTest) return;
    setSavingThresholds(true);
    try {
      await lactateApi.updateTest(expandedTest.id, {
        lt1_value: lt1Value ? Number(lt1Value) : null,
        lt1_lactate: lt1Lactate ? Number(lt1Lactate) : null,
        lt1_hr: lt1Hr ? Number(lt1Hr) : null,
        lt2_value: lt2Value ? Number(lt2Value) : null,
        lt2_lactate: lt2Lactate ? Number(lt2Lactate) : null,
        lt2_hr: lt2Hr ? Number(lt2Hr) : null,
      });
      // Re-fetch to update chart reference lines
      const updated = await lactateApi.getTest(expandedTest.id);
      setExpandedTest(updated);
      syncThresholdState(updated);
      // Also update the list item summary
      loadTests();
    } catch {
      // Silently fail
    } finally {
      setSavingThresholds(false);
    }
  }

  async function handleGasUploaded() {
    setShowGasUpload(false);
    if (expandedTest) {
      // Refresh expanded test to get has_gas_analysis flag
      const updated = await lactateApi.getTest(expandedTest.id);
      setExpandedTest(updated);
      loadGasAnalysis(expandedTest.id);
      loadTests(); // Refresh list for CPET badge
    }
  }

  async function handleDeleteGas() {
    if (!expandedTest || !confirm('Delete gas analysis data?')) return;
    setDeletingGas(true);
    try {
      await lactateApi.deleteGasAnalysis(expandedTest.id);
      setGasAnalysis(null);
      const updated = await lactateApi.getTest(expandedTest.id);
      setExpandedTest(updated);
      loadTests();
    } catch {
      // Silently fail
    } finally {
      setDeletingGas(false);
    }
  }

  // Group tests by test_type
  const grouped = tests.reduce<Record<string, LactateTestListItem[]>>((acc, t) => {
    const label = t.test_type === 'running' ? 'Running' : 'Cycling';
    if (!acc[label]) acc[label] = [];
    acc[label].push(t);
    return acc;
  }, {});

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const unitLabel = expandedTest ? (expandedTest.test_type === 'running' ? 'km/h' : 'W') : 'km/h';

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
          <p className="text-white/40 text-sm mb-3">No lactate tests yet</p>
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
        <div className="space-y-6">
          {Object.entries(grouped).map(([label, groupTests]) => (
            <div key={label}>
              <h3 className="font-heading uppercase tracking-wider text-sm text-accent mb-2">
                {label}
              </h3>
              <div className="space-y-2">
                {groupTests.map((t) => {
                  const tUnitLabel = t.test_type === 'running' ? 'km/h' : 'W';

                  return (
                    <div key={t.id} className="border border-secondary-muted/50 rounded-lg overflow-hidden">
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
                          <TypeBadge testType={t.test_type} />
                          {t.has_gas_analysis && <CpetBadge />}
                          {t.lt1_value != null && (
                            <span className="text-sm text-white">
                              LT1: {t.lt1_value} {tUnitLabel}
                            </span>
                          )}
                          {t.lt2_value != null && (
                            <span className="text-sm font-semibold text-white">
                              LT2: {t.lt2_value} {tUnitLabel}
                            </span>
                          )}
                          <span className="text-xs text-white/30">{t.stage_count} stages</span>
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
                              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4">
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
                              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4">
                                <path fillRule="evenodd" d="M5 3.25V4H2.75a.75.75 0 0 0 0 1.5h.3l.815 8.15A1.5 1.5 0 0 0 5.357 15h5.285a1.5 1.5 0 0 0 1.493-1.35l.815-8.15h.3a.75.75 0 0 0 0-1.5H11v-.75A2.25 2.25 0 0 0 8.75 1h-1.5A2.25 2.25 0 0 0 5 3.25Zm2.25-.75a.75.75 0 0 0-.75.75V4h3v-.75a.75.75 0 0 0-.75-.75h-1.5ZM6.05 6a.75.75 0 0 1 .787.713l.275 5.5a.75.75 0 0 1-1.498.075l-.275-5.5A.75.75 0 0 1 6.05 6Zm3.9 0a.75.75 0 0 1 .712.787l-.275 5.5a.75.75 0 0 1-1.498-.075l.275-5.5a.75.75 0 0 1 .786-.711Z" clipRule="evenodd" />
                              </svg>
                            </button>
                          )}
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            viewBox="0 0 16 16"
                            fill="currentColor"
                            className={`w-4 h-4 text-white/30 transition-transform ${expandedId === t.id ? 'rotate-180' : ''}`}
                          >
                            <path fillRule="evenodd" d="M4.22 6.22a.75.75 0 0 1 1.06 0L8 8.94l2.72-2.72a.75.75 0 1 1 1.06 1.06l-3.25 3.25a.75.75 0 0 1-1.06 0L4.22 7.28a.75.75 0 0 1 0-1.06Z" clipRule="evenodd" />
                          </svg>
                        </div>
                      </div>

                      {/* Expanded Detail */}
                      {expandedId === t.id && expandedTest && (
                        <div className="border-t border-secondary-muted/50 px-4 py-3 space-y-4 bg-primary-dark/30 overflow-hidden">
                          {/* Gas Analysis Actions */}
                          {!readOnly && (
                            <div className="flex items-center gap-2">
                              {!expandedTest.has_gas_analysis ? (
                                <button
                                  type="button"
                                  onClick={() => setShowGasUpload(true)}
                                  className="text-xs px-3 py-1 rounded bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 transition-colors"
                                >
                                  Upload Gas Data
                                </button>
                              ) : (
                                <button
                                  type="button"
                                  onClick={handleDeleteGas}
                                  disabled={deletingGas}
                                  className="text-xs px-3 py-1 rounded bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors disabled:opacity-50"
                                >
                                  {deletingGas ? 'Removing...' : 'Remove Gas Data'}
                                </button>
                              )}
                            </div>
                          )}

                          {/* Lactate Chart with gas overlays */}
                          <LactateChart
                            test={expandedTest}
                            gasAnalysis={gasAnalysis ? {
                              stage_averages: gasAnalysis.stage_averages,
                              fat_max_intensity: gasAnalysis.fat_max_intensity,
                            } : null}
                          />

                          {/* Fat Max Summary */}
                          {gasAnalysis && (
                            <FatMaxSummary
                              stageAverages={gasAnalysis.stage_averages}
                              lactateStages={expandedTest.stages}
                              unitLabel={unitLabel}
                              lt1Value={expandedTest.lt1_value}
                              lt2Value={expandedTest.lt2_value}
                            />
                          )}

                          {/* Threshold Editor */}
                          {!readOnly && <div className="border border-secondary-muted/50 rounded-lg p-3 space-y-3">
                            <div className="flex items-center justify-between">
                              <span className="text-sm text-white/60 font-medium">Thresholds</span>
                              <button
                                type="button"
                                onClick={handleAutoDetect}
                                disabled={expandedTest.stages.filter(s => s.intensity_value != null && s.blood_lactate_mmol != null).length < 5}
                                className="text-xs px-3 py-1 min-h-[44px] rounded bg-accent/20 text-accent hover:bg-accent/30 active:bg-accent/40 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                              >
                                Auto-Detect
                              </button>
                            </div>

                            {/* LT1 */}
                            <div>
                              <div className="text-xs text-white/40 mb-1">LT1</div>
                              <div className="grid grid-cols-3 gap-2">
                                <div>
                                  <label className="text-xs text-white/40">Value ({unitLabel})</label>
                                  <input
                                    type="number"
                                    step="any"
                                    value={lt1Value}
                                    onChange={(e) => setLt1Value(e.target.value)}
                                    className="input w-full"
                                    placeholder={unitLabel}
                                  />
                                </div>
                                <div>
                                  <label className="text-xs text-white/40">Lactate</label>
                                  <input
                                    type="number"
                                    step="0.01"
                                    value={lt1Lactate}
                                    onChange={(e) => setLt1Lactate(e.target.value)}
                                    className="input w-full"
                                    placeholder="mmol/L"
                                  />
                                </div>
                                <div>
                                  <label className="text-xs text-white/40">HR</label>
                                  <input
                                    type="number"
                                    value={lt1Hr}
                                    onChange={(e) => setLt1Hr(e.target.value)}
                                    className="input w-full"
                                    placeholder="bpm"
                                  />
                                </div>
                              </div>
                            </div>

                            {/* LT2 */}
                            <div>
                              <div className="text-xs text-white/40 mb-1">LT2</div>
                              <div className="grid grid-cols-3 gap-2">
                                <div>
                                  <label className="text-xs text-white/40">Value ({unitLabel})</label>
                                  <input
                                    type="number"
                                    step="any"
                                    value={lt2Value}
                                    onChange={(e) => setLt2Value(e.target.value)}
                                    className="input w-full"
                                    placeholder={unitLabel}
                                  />
                                </div>
                                <div>
                                  <label className="text-xs text-white/40">Lactate</label>
                                  <input
                                    type="number"
                                    step="0.01"
                                    value={lt2Lactate}
                                    onChange={(e) => setLt2Lactate(e.target.value)}
                                    className="input w-full"
                                    placeholder="mmol/L"
                                  />
                                </div>
                                <div>
                                  <label className="text-xs text-white/40">HR</label>
                                  <input
                                    type="number"
                                    value={lt2Hr}
                                    onChange={(e) => setLt2Hr(e.target.value)}
                                    className="input w-full"
                                    placeholder="bpm"
                                  />
                                </div>
                              </div>
                            </div>

                            <button
                              type="button"
                              onClick={handleSaveThresholds}
                              disabled={savingThresholds}
                              className="btn-primary text-sm px-4 py-1.5 w-full disabled:opacity-50"
                            >
                              {savingThresholds ? 'Saving...' : 'Save Thresholds'}
                            </button>
                          </div>}

                          {/* Threshold Gas Metrics Panel */}
                          {gasAnalysis && (expandedTest.lt1_value != null || expandedTest.lt2_value != null) && (
                            <ThresholdMetricsPanel
                              stageAverages={gasAnalysis.stage_averages}
                              lt1Value={expandedTest.lt1_value}
                              lt2Value={expandedTest.lt2_value}
                              unitLabel={unitLabel}
                            />
                          )}

                          {/* Stages Table */}
                          <div>
                            <table className="w-full text-sm">
                              <thead>
                                <tr className="text-white/40 text-xs">
                                  <th className="text-left py-1 pr-3">Stage</th>
                                  <th className="text-right py-1 px-3">
                                    {expandedTest.test_type === 'running' ? 'Speed' : 'Power'}
                                  </th>
                                  <th className="text-right py-1 px-3">Lactate</th>
                                  <th className="text-right py-1 px-3">HR</th>
                                  <th className="text-right py-1 pl-3">RPE</th>
                                </tr>
                              </thead>
                              <tbody>
                                {expandedTest.stages.map((s) => (
                                  <tr key={s.id} className="border-t border-secondary-muted/30">
                                    <td className="py-1.5 pr-3 text-white/60">{s.stage_number}</td>
                                    <td className="py-1.5 px-3 text-right text-white">
                                      {s.intensity_value} {unitLabel}
                                    </td>
                                    <td className="py-1.5 px-3 text-right text-white/80">
                                      {s.blood_lactate_mmol.toFixed(2)}
                                    </td>
                                    <td className="py-1.5 px-3 text-right text-white/80">
                                      {s.heart_rate_bpm ?? '-'}
                                    </td>
                                    <td className="py-1.5 pl-3 text-right text-white/60">
                                      {s.rpe ?? '-'}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>

                          {/* Notes */}
                          {expandedTest.notes && (
                            <p className="text-xs text-white/40">{expandedTest.notes}</p>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Form Modal */}
      {showForm && (
        <LactateTestForm
          athleteId={athleteId}
          existingTest={editTest}
          onClose={() => {
            setShowForm(false);
            setEditTest(null);
          }}
          onSaved={handleSaved}
        />
      )}

      {/* Gas Analysis Upload Modal */}
      {showGasUpload && expandedTest && (
        <GasAnalysisUpload
          testId={expandedTest.id}
          testType={expandedTest.test_type}
          onUploaded={handleGasUploaded}
          onClose={() => setShowGasUpload(false)}
        />
      )}
    </div>
  );
}
