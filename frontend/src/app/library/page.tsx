'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { ExerciseLibraryTable } from '@/components/library/ExerciseLibraryTable';
import { TemplateTable } from '@/components/library/TemplateTable';
import { ScrollableTabBar } from '@/components/ScrollableTabBar';

type LibraryTab = 'exercises' | 'templates';

export default function LibraryPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<LibraryTab>('exercises');

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

  if (user.role === 'athlete') {
    router.replace('/training');
    return null;
  }

  return (
    <div className="space-y-4 md:space-y-6">
      <h2 className="section-title text-base sm:text-lg">Library</h2>

      {/* Tab Toggle */}
      <ScrollableTabBar
        tabs={[
          { key: 'exercises', label: 'Exercises' },
          { key: 'templates', label: 'Templates' },
        ]}
        activeTab={activeTab}
        onTabChange={(key) => setActiveTab(key as LibraryTab)}
      />

      <div className="card">
        {activeTab === 'exercises' ? (
          <ExerciseLibraryTable />
        ) : (
          <TemplateTable />
        )}
      </div>
    </div>
  );
}
