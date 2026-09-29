'use client';

import { useState, useEffect, useCallback, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { programsApi } from '@/lib/api';
import { ScrollableTabBar } from '@/components/ScrollableTabBar';
import { ProgramCard } from '@/components/programs/ProgramCard';
import { ProgramDetailModal } from '@/components/programs/ProgramDetailModal';
import { ProgramFormModal } from '@/components/programs/ProgramFormModal';
import { BlockListView } from '@/components/blocks/BlockListView';
import { ProgrammeFormListView } from '@/components/programmes/ProgrammeFormListView';
import type { ProgramPackage, ProgramPackageDetail } from '@/lib/types';

type ProgramTab = 'browse' | 'blocks' | 'forms' | 'manage';
const CATEGORIES = ['All', 'Strength', 'Conditioning', 'Fight Camp', 'General'];

export default function ProgramsPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="inline-block w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <ProgramsPageContent />
    </Suspense>
  );
}

function ProgramsPageContent() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialTab = searchParams.get('tab') as ProgramTab | null;
  const [activeTab, setActiveTab] = useState<ProgramTab>(initialTab === 'forms' ? 'forms' : 'browse');
  const [programs, setPrograms] = useState<ProgramPackage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [detailProgram, setDetailProgram] = useState<ProgramPackageDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editProgram, setEditProgram] = useState<ProgramPackage | null>(null);

  const isAdmin = user?.role === 'admin';
  const isCoachOrAdmin = user?.role === 'coach' || user?.role === 'admin';

  const loadPrograms = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const category = selectedCategory === 'All' ? undefined : selectedCategory;
      const data = await programsApi.list(category);
      setPrograms(data);
    } catch {
      setError('Failed to load programs');
    } finally {
      setLoading(false);
    }
  }, [selectedCategory]);

  useEffect(() => {
    if (user) loadPrograms();
  }, [user, loadPrograms]);

  async function handleViewDetail(programId: string) {
    setDetailLoading(true);
    try {
      const detail = await programsApi.get(programId);
      setDetailProgram(detail);
    } catch {
      setError('Failed to load program details');
    } finally {
      setDetailLoading(false);
    }
  }

  async function handleInstall(programId: string) {
    try {
      await programsApi.install(programId);
      setPrograms(prev => prev.map(p => p.id === programId ? { ...p, is_installed: true } : p));
      if (detailProgram?.id === programId) {
        setDetailProgram(prev => prev ? { ...prev, is_installed: true } : null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to install program');
    }
  }

  async function handleUninstall(programId: string) {
    try {
      await programsApi.uninstall(programId);
      setPrograms(prev => prev.map(p => p.id === programId ? { ...p, is_installed: false } : p));
      if (detailProgram?.id === programId) {
        setDetailProgram(prev => prev ? { ...prev, is_installed: false } : null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to uninstall program');
    }
  }

  async function handleDeleteProgram(programId: string) {
    if (!window.confirm('Delete this program? This cannot be undone.')) return;
    try {
      await programsApi.delete(programId);
      setPrograms(prev => prev.filter(p => p.id !== programId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete program');
    }
  }

  async function handleTogglePublish(program: ProgramPackage) {
    try {
      const updated = await programsApi.update(program.id, { is_published: !program.is_published });
      setPrograms(prev => prev.map(p => p.id === program.id ? { ...p, ...updated } : p));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update program');
    }
  }

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="inline-block w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) {
    router.push('/login');
    return null;
  }

  const tabs = [
    { key: 'browse', label: 'Browse' },
    ...(isCoachOrAdmin ? [{ key: 'blocks', label: 'My Blocks' }] : []),
    ...(isCoachOrAdmin ? [{ key: 'forms', label: 'My Forms' }] : []),
    ...(isAdmin ? [{ key: 'manage', label: 'Manage' }] : []),
  ];

  return (
    <div className="space-y-4 md:space-y-6">
      <h2 className="section-title text-base sm:text-lg">Programs</h2>

      {tabs.length > 1 && (
        <ScrollableTabBar
          tabs={tabs}
          activeTab={activeTab}
          onTabChange={(key) => setActiveTab(key as ProgramTab)}
        />
      )}

      {/* Category Filter Chips */}
      {activeTab === 'browse' && (
        <div className="flex flex-wrap gap-2">
          {CATEGORIES.map(cat => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                selectedCategory === cat
                  ? 'bg-accent text-[#090A3D]'
                  : 'bg-white/5 text-white/60 hover:bg-white/10 hover:text-white'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-sm text-red-400">
          {error}
          <button onClick={() => setError(null)} className="ml-2 text-red-300 hover:text-red-200">&times;</button>
        </div>
      )}

      {activeTab === 'browse' && (
        <div className="card">
          {loading ? (
            <div className="text-center py-12">
              <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
            </div>
          ) : programs.length === 0 ? (
            <p className="text-white/60 text-sm py-12 text-center">
              No programs available yet.
            </p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {programs.map(program => (
                <ProgramCard
                  key={program.id}
                  program={program}
                  onViewDetail={() => handleViewDetail(program.id)}
                  onInstall={() => handleInstall(program.id)}
                  onUninstall={() => handleUninstall(program.id)}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'blocks' && isCoachOrAdmin && (
        <BlockListView />
      )}

      {activeTab === 'forms' && isCoachOrAdmin && (
        <ProgrammeFormListView />
      )}

      {activeTab === 'manage' && isAdmin && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-white/60">Manage training programs</p>
            <button
              onClick={() => { setEditProgram(null); setShowCreateModal(true); }}
              className="px-4 py-2 min-h-[44px] rounded text-sm font-medium bg-accent text-[#090A3D] hover:bg-accent/80 transition-colors"
            >
              + New Program
            </button>
          </div>

          {loading ? (
            <div className="text-center py-8">
              <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
            </div>
          ) : programs.length === 0 ? (
            <p className="text-white/60 text-sm py-8 text-center">No programs created yet.</p>
          ) : (
            <div className="space-y-3">
              {programs.map(program => (
                <div key={program.id} className="border border-secondary-muted rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-sm">{program.program_name}</p>
                      <p className="text-xs text-white/40">
                        {program.category} &middot; {program.template_count} template{program.template_count !== 1 ? 's' : ''}
                        {program.is_published ? (
                          <span className="ml-2 text-green-400">Published</span>
                        ) : (
                          <span className="ml-2 text-yellow-400">Draft</span>
                        )}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleTogglePublish(program)}
                        className="px-3 py-1.5 rounded text-xs font-medium bg-white/5 text-white/60 hover:bg-white/10 transition-colors"
                      >
                        {program.is_published ? 'Unpublish' : 'Publish'}
                      </button>
                      <button
                        onClick={() => handleViewDetail(program.id)}
                        className="px-3 py-1.5 rounded text-xs font-medium bg-white/5 text-white/60 hover:bg-white/10 transition-colors"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteProgram(program.id)}
                        className="px-3 py-1.5 rounded text-xs font-medium bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Detail Modal */}
      {detailProgram && (
        <ProgramDetailModal
          program={detailProgram}
          isAdmin={isAdmin}
          onClose={() => setDetailProgram(null)}
          onInstall={() => handleInstall(detailProgram.id)}
          onUninstall={() => handleUninstall(detailProgram.id)}
          onProgramUpdated={loadPrograms}
        />
      )}

      {/* Create/Edit Modal */}
      {showCreateModal && (
        <ProgramFormModal
          program={editProgram}
          onClose={() => { setShowCreateModal(false); setEditProgram(null); }}
          onSaved={() => { setShowCreateModal(false); setEditProgram(null); loadPrograms(); }}
        />
      )}

      {/* Suppress unused var warning for detailLoading */}
      {detailLoading && null}
    </div>
  );
}
