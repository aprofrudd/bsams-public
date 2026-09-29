'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { useAthleteContext } from '@/lib/contexts/AthleteContext';
import { useIsReadOnly } from '@/lib/hooks/useIsReadOnly';
import { DataViewControls } from '@/components/DataViewControls';
import { PerformanceTable } from '@/components/PerformanceTable';
import { PerformanceGraph } from '@/components/PerformanceGraph';
import { ZScoreRadar } from '@/components/ZScoreRadar';
import { DataSharingConsent } from '@/components/DataSharingConsent';
import { SharedDataView } from '@/components/SharedDataView';
import { VbtProfilesView } from '@/components/testing/VbtProfilesView';
import { VbtRadar } from '@/components/VbtRadar';
import { MobilityView } from '@/components/testing/MobilityView';
import { LactateProfilesView } from '@/components/testing/LactateProfilesView';
import { AirBikeView } from '@/components/testing/AirBikeView';
import { EventFormModal } from '@/components/EventFormModal';
import { ScrollableTabBar } from '@/components/ScrollableTabBar';
import NoAthleteSelected from '@/components/NoAthleteSelected';
import { METRIC_DEFINITIONS } from '@/lib/metricRegistry';
import type { ReferenceGroup, ViewMode, BenchmarkSource } from '@/lib/types';

const JUMP_METRIC_KEYS = METRIC_DEFINITIONS.filter(m => m.group === 'jump').map(m => m.key);
const ISOMETRIC_METRIC_KEYS = METRIC_DEFINITIONS.filter(m => m.group === 'isometric').map(m => m.key);

type TestingTab = 'metrics' | 'vbt' | 'mobility' | 'isometrics' | 'lactate' | 'air-bike';

export default function TestingPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const { selectedAthlete, setSelectedAthlete } = useAthleteContext();
  const readOnly = useIsReadOnly();
  const [referenceGroup, setReferenceGroup] = useState<ReferenceGroup>('cohort');
  const [viewMode, setViewMode] = useState<ViewMode>('table');
  const [selectedMetric, setSelectedMetric] = useState<string>('height_cm');
  const [showRadar, setShowRadar] = useState(false);
  const [benchmarkSource, setBenchmarkSource] = useState<BenchmarkSource>('own');
  const [adminTab, setAdminTab] = useState<'my_athletes' | 'shared_data'>('my_athletes');
  const [dataVersion, setDataVersion] = useState(0);
  const [testingTab, setTestingTab] = useState<TestingTab>('metrics');
  const [tabHasMetrics, setTabHasMetrics] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);

  useEffect(() => {
    if (!loading && !user) {
      router.replace('/login');
    }
  }, [loading, user, router]);

  useEffect(() => {
    setShowRadar(false);
  }, [selectedAthlete]);

  useEffect(() => {
    setShowRadar(false);
    setTabHasMetrics(true); // Reset while loading
    // Reset selected metric to a sensible default for the tab
    if (testingTab === 'isometrics') {
      setSelectedMetric(ISOMETRIC_METRIC_KEYS[0]);
    } else if (testingTab === 'metrics') {
      setSelectedMetric('height_cm');
    }
  }, [testingTab]);

  if (loading || !user) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-4 md:space-y-6">
      {/* Page Header + Admin Toggle */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="section-title text-base sm:text-lg">{readOnly ? 'My Tests' : 'Testing'}</h2>
        <div className="flex items-center gap-3">
          {user?.role === 'coach' && <DataSharingConsent />}
          {user?.role === 'admin' && (
            <div className="flex rounded-lg overflow-hidden border border-secondary-muted">
              <button
                onClick={() => setAdminTab('my_athletes')}
                className={`px-4 py-2.5 min-h-[44px] text-xs font-heading uppercase tracking-wider transition-colors ${
                  adminTab === 'my_athletes'
                    ? 'bg-accent text-primary active:bg-accent'
                    : 'bg-primary-dark text-white/60 hover:bg-secondary-muted active:bg-secondary-muted'
                }`}
              >
                My Athletes
              </button>
              <button
                onClick={() => setAdminTab('shared_data')}
                className={`px-4 py-2.5 min-h-[44px] text-xs font-heading uppercase tracking-wider transition-colors ${
                  adminTab === 'shared_data'
                    ? 'bg-accent text-primary active:bg-accent'
                    : 'bg-primary-dark text-white/60 hover:bg-secondary-muted active:bg-secondary-muted'
                }`}
              >
                Shared Data
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Shared Data View (admin only) */}
      {user?.role === 'admin' && adminTab === 'shared_data' ? (
        <SharedDataView />
      ) : (
        <div className="space-y-4 md:space-y-6">
          {/* Metrics / VBT Toggle */}
          <ScrollableTabBar
            tabs={[
              { key: 'metrics', label: 'Jump Assessments' },
              { key: 'vbt', label: 'VBT Assessments' },
              { key: 'mobility', label: 'Mobility Assessments' },
              { key: 'isometrics', label: 'Isometrics' },
              { key: 'lactate', label: 'Lactate Profile' },
              { key: 'air-bike', label: 'Air Bike' },
            ]}
            activeTab={testingTab}
            onTabChange={(key) => setTestingTab(key as TestingTab)}
          />

          {testingTab === 'metrics' ? (
            <>
              {/* Controls — full width */}
              <DataViewControls
                referenceGroup={referenceGroup}
                onReferenceGroupChange={setReferenceGroup}
                viewMode={viewMode}
                onViewModeChange={setViewMode}
                selectedMetric={selectedMetric}
                onMetricChange={setSelectedMetric}
                athleteId={selectedAthlete?.id}
                disabled={!selectedAthlete}
                benchmarkSource={benchmarkSource}
                onBenchmarkSourceChange={setBenchmarkSource}
                role={user?.role}
                dataVersion={dataVersion}
                metricFilter={JUMP_METRIC_KEYS}
                onMetricsAvailable={(count) => setTabHasMetrics(count > 0)}
              />

              {/* Data Display — full width */}
              {selectedAthlete ? (
                tabHasMetrics ? (
                  <>
                    <div className="card">
                      {viewMode === 'table' ? (
                        <PerformanceTable
                          athleteId={selectedAthlete.id}
                          referenceGroup={referenceGroup}
                          metric={selectedMetric}
                          benchmarkSource={benchmarkSource}
                          onDataChanged={() => setDataVersion((v) => v + 1)}
                          allowedGroups={['jump']}
                          readOnly={readOnly}
                        />
                      ) : (
                        <PerformanceGraph
                          athleteId={selectedAthlete.id}
                          referenceGroup={referenceGroup}
                          metric={selectedMetric}
                          athleteGender={selectedAthlete.gender}
                          benchmarkSource={benchmarkSource}
                        />
                      )}
                    </div>

                    {/* Z-Score Radar Chart */}
                    <div className="card">
                      {showRadar ? (
                        <>
                          <ZScoreRadar
                            athleteId={selectedAthlete.id}
                            referenceGroup={referenceGroup}
                            benchmarkSource={benchmarkSource}
                            metricFilter={JUMP_METRIC_KEYS}
                          />
                          <button
                            onClick={() => setShowRadar(false)}
                            className="mt-4 w-full px-4 py-3 min-h-[44px] text-sm font-medium rounded bg-[#2D5585]/30 text-white/60 hover:bg-[#2D5585]/50 transition-colors"
                          >
                            Hide Radar
                          </button>
                        </>
                      ) : (
                        <button
                          onClick={() => setShowRadar(true)}
                          className="w-full px-4 py-3 min-h-[44px] text-sm font-heading uppercase tracking-wider rounded bg-accent text-[#090A3D] hover:bg-accent/80 transition-colors"
                        >
                          Generate Radar Plot
                        </button>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="card text-center py-12 md:py-16">
                    <p className="text-white/40 font-heading uppercase tracking-wider text-sm mb-4">
                      No jump analysis data yet
                    </p>
                    {!readOnly && (
                      <button
                        onClick={() => setShowAddModal(true)}
                        className="btn-primary px-6"
                      >
                        + Add Data
                      </button>
                    )}
                    {!readOnly && showAddModal && (
                      <EventFormModal
                        athleteId={selectedAthlete.id}
                        onClose={() => setShowAddModal(false)}
                        onSaved={() => { setShowAddModal(false); setDataVersion((v) => v + 1); }}
                        allowedGroups={['jump']}
                      />
                    )}
                  </div>
                )
              ) : (
                <NoAthleteSelected message="Select an athlete to view performance data" />
              )}
            </>
          ) : testingTab === 'vbt' ? (
            /* VBT Profiles Tab */
            selectedAthlete ? (
              <div className="space-y-4 md:space-y-6">
                <div className="card">
                  <VbtProfilesView athleteId={selectedAthlete.id} readOnly={readOnly} />
                </div>
                <div className="card">
                  {showRadar ? (
                    <>
                      <VbtRadar athleteId={selectedAthlete.id} />
                      <button
                        onClick={() => setShowRadar(false)}
                        className="mt-4 w-full px-4 py-3 min-h-[44px] text-sm font-medium rounded bg-[#2D5585]/30 text-white/60 hover:bg-[#2D5585]/50 transition-colors"
                      >
                        Hide Radar
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() => setShowRadar(true)}
                      className="w-full px-4 py-3 min-h-[44px] text-sm font-heading uppercase tracking-wider rounded bg-accent text-[#090A3D] hover:bg-accent/80 transition-colors"
                    >
                      Generate VBT Radar
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <NoAthleteSelected message="Select an athlete to view VBT profiles" />
            )
          ) : testingTab === 'mobility' ? (
            /* Mobility Tab */
            selectedAthlete ? (
              <div className="card">
                <MobilityView athleteId={selectedAthlete.id} readOnly={readOnly} />
              </div>
            ) : (
              <NoAthleteSelected message="Select an athlete to view mobility assessments" />
            )
          ) : testingTab === 'isometrics' ? (
            /* Isometrics Tab */
            selectedAthlete ? (
              <>
                <DataViewControls
                  referenceGroup={referenceGroup}
                  onReferenceGroupChange={setReferenceGroup}
                  viewMode={viewMode}
                  onViewModeChange={setViewMode}
                  selectedMetric={selectedMetric}
                  onMetricChange={setSelectedMetric}
                  athleteId={selectedAthlete?.id}
                  disabled={!selectedAthlete}
                  benchmarkSource={benchmarkSource}
                  onBenchmarkSourceChange={setBenchmarkSource}
                  role={user?.role}
                  dataVersion={dataVersion}
                  metricFilter={ISOMETRIC_METRIC_KEYS}
                  onMetricsAvailable={(count) => setTabHasMetrics(count > 0)}
                />

                {tabHasMetrics ? (
                  <>
                    <div className="card">
                      {viewMode === 'table' ? (
                        <PerformanceTable
                          athleteId={selectedAthlete.id}
                          referenceGroup={referenceGroup}
                          metric={selectedMetric}
                          benchmarkSource={benchmarkSource}
                          onDataChanged={() => setDataVersion((v) => v + 1)}
                          allowedGroups={['isometric']}
                          readOnly={readOnly}
                        />
                      ) : (
                        <PerformanceGraph
                          athleteId={selectedAthlete.id}
                          referenceGroup={referenceGroup}
                          metric={selectedMetric}
                          athleteGender={selectedAthlete.gender}
                          benchmarkSource={benchmarkSource}
                        />
                      )}
                    </div>

                    <div className="card">
                      {showRadar ? (
                        <>
                          <ZScoreRadar
                            athleteId={selectedAthlete.id}
                            referenceGroup={referenceGroup}
                            benchmarkSource={benchmarkSource}
                            metricFilter={ISOMETRIC_METRIC_KEYS}
                          />
                          <button
                            onClick={() => setShowRadar(false)}
                            className="mt-4 w-full px-4 py-3 min-h-[44px] text-sm font-medium rounded bg-[#2D5585]/30 text-white/60 hover:bg-[#2D5585]/50 transition-colors"
                          >
                            Hide Radar
                          </button>
                        </>
                      ) : (
                        <button
                          onClick={() => setShowRadar(true)}
                          className="w-full px-4 py-3 min-h-[44px] text-sm font-heading uppercase tracking-wider rounded bg-accent text-[#090A3D] hover:bg-accent/80 transition-colors"
                        >
                          Generate Radar Plot
                        </button>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="card text-center py-12 md:py-16">
                    <p className="text-white/40 font-heading uppercase tracking-wider text-sm mb-4">
                      No isometric data yet
                    </p>
                    {!readOnly && (
                      <button
                        onClick={() => setShowAddModal(true)}
                        className="btn-primary px-6"
                      >
                        + Add Data
                      </button>
                    )}
                    {!readOnly && showAddModal && (
                      <EventFormModal
                        athleteId={selectedAthlete.id}
                        onClose={() => setShowAddModal(false)}
                        onSaved={() => { setShowAddModal(false); setDataVersion((v) => v + 1); }}
                        allowedGroups={['isometric']}
                      />
                    )}
                  </div>
                )}
              </>
            ) : (
              <NoAthleteSelected message="Select an athlete to view isometric data" />
            )
          ) : testingTab === 'lactate' ? (
            /* Lactate Tab */
            selectedAthlete ? (
              <div className="card">
                <LactateProfilesView athleteId={selectedAthlete.id} readOnly={readOnly} />
              </div>
            ) : (
              <NoAthleteSelected message="Select an athlete to view lactate tests" />
            )
          ) : testingTab === 'air-bike' ? (
            /* Air Bike Tab */
            selectedAthlete ? (
              <div className="card">
                <AirBikeView athleteId={selectedAthlete.id} athleteWeight={selectedAthlete.body_mass_kg ?? null} readOnly={readOnly} />
              </div>
            ) : (
              <NoAthleteSelected message="Select an athlete to view air bike tests" />
            )
          ) : null}
        </div>
      )}
    </div>
  );
}
