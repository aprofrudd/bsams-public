'use client';

import { useState, useEffect, useRef, useMemo } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { useAthleteContext } from '@/lib/contexts/AthleteContext';
import { athletesApi } from '@/lib/api';
import { AthleteCreateModal } from './AthleteCreateModal';
import type { Athlete } from '@/lib/types';

interface NavItem {
  label: string;
  athleteLabel?: string;
  href: string;
  matchPaths: string[];
  group: 'athlete' | 'coach';
  roles?: ('coach' | 'admin' | 'athlete')[];
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', athleteLabel: 'Dashboard', href: '/dashboard', matchPaths: ['/dashboard'], group: 'athlete', roles: ['athlete'] },
  { label: 'Training', athleteLabel: 'My Training', href: '/training', matchPaths: ['/training'], group: 'athlete', roles: ['coach', 'admin', 'athlete'] },
  { label: 'Library', href: '/library', matchPaths: ['/library'], group: 'athlete', roles: ['coach', 'admin'] },
  { label: 'Programs', href: '/programs', matchPaths: ['/programs'], group: 'athlete', roles: ['coach', 'admin', 'athlete'] },
  { label: 'Testing', athleteLabel: 'My Tests', href: '/testing', matchPaths: ['/testing'], group: 'athlete', roles: ['coach', 'admin', 'athlete'] },
  { label: 'Reports', href: '/test-report', matchPaths: ['/test-report'], group: 'coach', roles: ['coach', 'admin'] },
  { label: 'Consult', href: '/consult', matchPaths: ['/consult'], group: 'coach', roles: ['coach', 'admin', 'athlete'] },
  { label: 'Analysis', href: '/database-analysis', matchPaths: ['/database-analysis'], group: 'coach', roles: ['admin'] },
  { label: 'Combine', href: '/combine', matchPaths: ['/combine'], group: 'coach', roles: ['admin', 'coach'] },
  { label: 'Upload', href: '/upload', matchPaths: ['/upload'], group: 'coach', roles: ['admin', 'coach'] },
];

const ATHLETE_PAGES = ['/dashboard', '/athlete-info', '/testing', '/training', '/test-report'];

export function AppHeader() {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const { selectedAthlete, setSelectedAthlete, athleteVersion } = useAthleteContext();

  const [athletes, setAthletes] = useState<Athlete[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  const isAthleteRole = user?.role === 'athlete';

  const visibleNavItems = useMemo(() =>
    NAV_ITEMS.filter(item => !item.roles || item.roles.includes(user?.role as any)),
    [user?.role]
  );

  // Load athletes when user is authenticated (skip for athlete role)
  // athleteVersion triggers reload when onboarding wizard creates an athlete
  useEffect(() => {
    if (user && !isAthleteRole) {
      loadAthletes();
    }
  }, [user, isAthleteRole, athleteVersion]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  // Focus search when dropdown opens
  useEffect(() => {
    if (isOpen && searchRef.current) {
      searchRef.current.focus();
    }
  }, [isOpen]);

  // Close mobile menu on route change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname]);

  async function loadAthletes() {
    try {
      setIsLoading(true);
      const data = await athletesApi.list();
      setAthletes(data);
      if (!selectedAthlete) {
        try {
          const savedId = localStorage.getItem('bsams-selected-athlete');
          if (savedId) {
            const match = data.find((a: Athlete) => a.id === savedId);
            if (match) setSelectedAthlete(match);
          }
        } catch { /* ignore */ }
      }
    } catch {
      // Silently handle — dropdown will show empty state
    } finally {
      setIsLoading(false);
    }
  }

  // Build duplicate names set
  const duplicateNames = useMemo(() => {
    const nameCounts: Record<string, number> = {};
    for (const a of athletes) {
      const key = a.name.toLowerCase().trim();
      nameCounts[key] = (nameCounts[key] || 0) + 1;
    }
    const dupes = new Set<string>();
    Object.entries(nameCounts).forEach(([key, count]) => {
      if (count > 1) dupes.add(key);
    });
    return dupes;
  }, [athletes]);

  const filteredAthletes = athletes.filter((a) =>
    a.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  function handleSelectAthlete(athlete: Athlete) {
    setSelectedAthlete(athlete);
    setIsOpen(false);
    setSearchQuery('');
  }

  // Only show athlete selector on pages that use athlete context
  const showAthleteSelector = user && ATHLETE_PAGES.some(p => pathname.startsWith(p));

  return (
    <>
      <header className="bg-primary-dark border-b border-secondary-muted sticky top-0 z-50">
        <div className="flex items-center justify-between max-w-7xl mx-auto px-4 sm:px-6 h-14">
          {/* Left: Logo + Hamburger (mobile) + Nav (desktop) */}
          <div className="flex items-center gap-4 md:gap-6">
            <div className="flex flex-col items-start leading-tight">
              <h1 className="font-heading text-lg sm:text-xl font-bold text-accent tracking-wider uppercase">
                BSAMS
              </h1>
              <span className="text-[10px] sm:text-xs text-white/50 tracking-widest uppercase">
                Research Preview
              </span>
            </div>

            {/* Hamburger button — visible below md */}
            {user && (
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="md:hidden flex items-center justify-center w-10 h-10 min-h-[44px] min-w-[44px] rounded text-white/60 hover:text-white hover:bg-white/10 active:text-white active:bg-white/10 active:scale-[0.97] transition-colors"
                aria-label="Toggle menu"
              >
                {mobileMenuOpen ? (
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
                    <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
                  </svg>
                ) : (
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
                    <path fillRule="evenodd" d="M2 4.75A.75.75 0 012.75 4h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 4.75zm0 10.5a.75.75 0 01.75-.75h14.5a.75.75 0 010 1.5H2.75a.75.75 0 01-.75-.75zM2 10a.75.75 0 01.75-.75h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 10z" clipRule="evenodd" />
                  </svg>
                )}
              </button>
            )}

            {/* Desktop nav — hidden below md */}
            {user && (
              <nav className="hidden md:flex items-center gap-1">
                {visibleNavItems.map((item, i) => {
                  const isActive = item.matchPaths.includes(pathname);
                  const prevGroup = i > 0 ? visibleNavItems[i - 1].group : item.group;
                  return (
                    <span key={item.href} className="flex items-center">
                      {item.group !== prevGroup && (
                        <span className="w-px h-5 bg-secondary-muted mx-1.5" />
                      )}
                      <Link
                        href={item.href}
                        className={`font-heading text-xs sm:text-sm uppercase tracking-wider px-2 md:px-3 py-2 min-h-[44px] flex items-center rounded-md transition-colors ${
                          isActive
                            ? 'text-accent bg-accent/10'
                            : 'text-white/50 hover:text-white hover:bg-white/5 active:text-white active:bg-white/5'
                        }`}
                      >
                        {isAthleteRole && item.athleteLabel ? item.athleteLabel : item.label}
                      </Link>
                    </span>
                  );
                })}
              </nav>
            )}
          </div>

          {/* Center: Athlete Selector */}
          {showAthleteSelector && (
            isAthleteRole ? (
              /* Static display for athlete role */
              <div className="flex items-center gap-2 px-3 sm:px-4 py-2 min-h-[44px]">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent shrink-0">
                  <path d="M10 8a3 3 0 100-6 3 3 0 000 6zM3.465 14.493a1.23 1.23 0 00.41 1.412A9.957 9.957 0 0010 18c2.31 0 4.438-.784 6.131-2.1.43-.333.604-.903.408-1.41a7.002 7.002 0 00-13.074.003z" />
                </svg>
                <span className="font-heading text-xs sm:text-sm uppercase tracking-wider truncate max-w-[80px] sm:max-w-[160px] text-white">
                  {selectedAthlete?.name || 'Loading...'}
                </span>
              </div>
            ) : (
            <div ref={dropdownRef} className="relative">
              <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 px-3 sm:px-4 py-2 min-h-[44px] rounded-lg border border-secondary-muted hover:border-accent/50 active:border-accent/50 active:scale-[0.97] transition-colors bg-primary-dark min-w-0 sm:min-w-[220px]"
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent shrink-0">
                  <path d="M10 8a3 3 0 100-6 3 3 0 000 6zM3.465 14.493a1.23 1.23 0 00.41 1.412A9.957 9.957 0 0010 18c2.31 0 4.438-.784 6.131-2.1.43-.333.604-.903.408-1.41a7.002 7.002 0 00-13.074.003z" />
                </svg>
                <span className="font-heading text-xs sm:text-sm uppercase tracking-wider truncate max-w-[80px] sm:max-w-[160px]">
                  {selectedAthlete ? selectedAthlete.name : 'Select Athlete'}
                </span>
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className={`w-4 h-4 text-white/40 shrink-0 transition-transform ${isOpen ? 'rotate-180' : ''}`}>
                  <path fillRule="evenodd" d="M5.22 8.22a.75.75 0 011.06 0L10 11.94l3.72-3.72a.75.75 0 111.06 1.06l-4.25 4.25a.75.75 0 01-1.06 0L5.22 9.28a.75.75 0 010-1.06z" clipRule="evenodd" />
                </svg>
              </button>

              {/* Dropdown Panel */}
              {isOpen && (
                <div className="fixed top-[3.75rem] left-2 right-2 sm:absolute sm:top-full sm:mt-2 sm:right-auto sm:left-1/2 sm:-translate-x-1/2 sm:w-80 max-w-80 bg-primary-dark border border-secondary-muted rounded-xl shadow-2xl shadow-black/50 overflow-hidden z-50">
                  {/* Search */}
                  <div className="p-3 border-b border-secondary-muted/50">
                    <input
                      ref={searchRef}
                      type="text"
                      placeholder="Search athletes..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="input w-full text-sm"
                    />
                  </div>

                  {/* Athlete list */}
                  <div className="max-h-[50vh] sm:max-h-64 overflow-y-auto">
                    {isLoading ? (
                      <div className="text-center py-6">
                        <div className="inline-block w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                      </div>
                    ) : filteredAthletes.length === 0 ? (
                      <div className="text-white/40 text-sm py-6 text-center">
                        {searchQuery ? 'No athletes found' : (
                          <button
                            onClick={() => {
                              setShowCreateModal(true);
                              setIsOpen(false);
                            }}
                            className="text-accent hover:text-accent/80 transition-colors"
                          >
                            No athletes yet — add your first
                          </button>
                        )}
                      </div>
                    ) : (
                      filteredAthletes.map((athlete) => (
                        <button
                          key={athlete.id}
                          onClick={() => handleSelectAthlete(athlete)}
                          className={`w-full text-left px-4 py-3 min-h-[44px] flex items-center justify-between transition-colors ${
                            selectedAthlete?.id === athlete.id
                              ? 'bg-accent/15 text-white'
                              : 'hover:bg-white/5 active:bg-white/5 text-white/80'
                          }`}
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <span className="font-medium text-sm truncate">{athlete.name}</span>
                            {duplicateNames.has(athlete.name.toLowerCase().trim()) && (
                              <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded bg-yellow-500/20 text-yellow-400 shrink-0">
                                Dup
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-2 shrink-0">
                            <span className="text-xs text-white/30 capitalize">{athlete.gender}</span>
                            {selectedAthlete?.id === athlete.id && (
                              <span
                                role="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setIsOpen(false);
                                  router.push('/athlete-info');
                                }}
                                className="p-2 min-h-[44px] min-w-[44px] flex items-center justify-center rounded hover:bg-white/10 active:bg-white/10 active:scale-[0.97] transition-colors"
                                title="View profile"
                              >
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-3.5 h-3.5 text-accent">
                                  <path d="M2.695 14.763l-1.262 3.154a.5.5 0 00.65.65l3.155-1.262a4 4 0 001.343-.885L17.5 5.5a2.121 2.121 0 00-3-3L3.58 13.42a4 4 0 00-.885 1.343z" />
                                </svg>
                              </span>
                            )}
                          </div>
                        </button>
                      ))
                    )}
                  </div>

                  {/* Add Athlete footer */}
                  <div className="p-2 border-t border-secondary-muted/50">
                    <button
                      onClick={() => {
                        setShowCreateModal(true);
                        setIsOpen(false);
                      }}
                      className="w-full px-3 py-2.5 min-h-[44px] rounded-lg text-sm font-medium bg-accent/10 text-accent hover:bg-accent/20 active:bg-accent/20 active:scale-[0.97] transition-colors"
                    >
                      + Add Athlete
                    </button>
                  </div>
                </div>
              )}
            </div>
            )
          )}

          {/* Right: User info + Logout */}
          <div className="flex items-center gap-3">
            {user ? (
              <>
                <span className="text-white/40 text-xs hidden md:inline truncate max-w-[140px]">
                  {user.email}
                </span>
                <Link
                  href="/help"
                  className="text-white/40 hover:text-white active:text-white py-2 px-2 min-h-[44px] flex items-center transition-colors"
                  title="Help"
                >
                  <span className="w-4 h-4 rounded-full border border-current flex items-center justify-center text-[10px] font-bold leading-none">?</span>
                </Link>
                <Link
                  href="/settings"
                  className="text-white/40 hover:text-white active:text-white py-2 px-2 min-h-[44px] flex items-center transition-colors"
                  title="Settings"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                    <path fillRule="evenodd" d="M7.84 1.804A1 1 0 018.82 1h2.36a1 1 0 01.98.804l.331 1.652a6.993 6.993 0 011.929 1.115l1.598-.54a1 1 0 011.186.447l1.18 2.044a1 1 0 01-.205 1.251l-1.267 1.113a7.047 7.047 0 010 2.228l1.267 1.113a1 1 0 01.206 1.25l-1.18 2.045a1 1 0 01-1.187.447l-1.598-.54a6.993 6.993 0 01-1.929 1.115l-.33 1.652a1 1 0 01-.98.804H8.82a1 1 0 01-.98-.804l-.331-1.652a6.993 6.993 0 01-1.929-1.115l-1.598.54a1 1 0 01-1.186-.447l-1.18-2.044a1 1 0 01.205-1.251l1.267-1.114a7.05 7.05 0 010-2.227L1.821 7.773a1 1 0 01-.206-1.25l1.18-2.045a1 1 0 011.187-.447l1.598.54A6.993 6.993 0 017.51 3.456l.33-1.652zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
                  </svg>
                </Link>
                <button
                  onClick={logout}
                  className="text-white/40 hover:text-white active:text-white text-xs py-2 px-2 min-h-[44px] flex items-center transition-colors"
                >
                  Log Out
                </button>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  className="text-white/60 hover:text-white text-sm px-2 min-h-[44px] flex items-center transition-colors"
                >
                  Log In
                </Link>
                <Link
                  href="/login"
                  className="bg-accent hover:bg-accent-hover text-primary font-semibold text-sm px-4 min-h-[44px] flex items-center justify-center rounded-lg transition-colors"
                >
                  Sign Up
                </Link>
              </>
            )}
          </div>
        </div>

        {/* Mobile nav drawer — slides below header */}
        {user && mobileMenuOpen && (
          <nav className="md:hidden border-t border-secondary-muted/50 bg-primary-dark">
            <div className="max-w-7xl mx-auto px-4 py-2 flex flex-col gap-1">
              {visibleNavItems.map((item, i) => {
                const isActive = item.matchPaths.includes(pathname);
                const prevGroup = i > 0 ? visibleNavItems[i - 1].group : item.group;
                return (
                  <div key={item.href}>
                    {item.group !== prevGroup && (
                      <div className="h-px bg-secondary-muted/50 my-1" />
                    )}
                    <Link
                      href={item.href}
                      className={`block font-heading text-sm uppercase tracking-wider px-3 py-2.5 min-h-[44px] rounded-md transition-colors ${
                        isActive
                          ? 'text-accent bg-accent/10'
                          : 'text-white/50 hover:text-white hover:bg-white/5 active:text-white active:bg-white/5'
                      }`}
                    >
                      {isAthleteRole && item.athleteLabel ? item.athleteLabel : item.label}
                    </Link>
                  </div>
                );
              })}
              <div className="h-px bg-secondary-muted/50 my-1" />
              <Link
                href="/help"
                className={`block font-heading text-sm uppercase tracking-wider px-3 py-2.5 min-h-[44px] rounded-md transition-colors ${
                  pathname === '/help'
                    ? 'text-accent bg-accent/10'
                    : 'text-white/50 hover:text-white hover:bg-white/5 active:text-white active:bg-white/5'
                }`}
              >
                Help
              </Link>
              <Link
                href="/settings"
                className={`block font-heading text-sm uppercase tracking-wider px-3 py-2.5 min-h-[44px] rounded-md transition-colors ${
                  pathname === '/settings'
                    ? 'text-accent bg-accent/10'
                    : 'text-white/50 hover:text-white hover:bg-white/5 active:text-white active:bg-white/5'
                }`}
              >
                Settings
              </Link>
            </div>
          </nav>
        )}
      </header>

      {/* Modals */}
      {showCreateModal && (
        <AthleteCreateModal
          onClose={() => setShowCreateModal(false)}
          onCreated={(created) => {
            setShowCreateModal(false);
            setAthletes((prev) => [...prev, created]);
            setSelectedAthlete(created);
          }}
        />
      )}
    </>
  );
}
