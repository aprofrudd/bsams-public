'use client';

import { useRef, useState, useEffect, useCallback } from 'react';

interface Tab {
  key: string;
  label: string;
}

interface ScrollableTabBarProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (key: string) => void;
}

export function ScrollableTabBar({ tabs, activeTab, onTabChange }: ScrollableTabBarProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const tabRefs = useRef<Map<string, HTMLButtonElement>>(new Map());
  const [showLeftFade, setShowLeftFade] = useState(false);
  const [showRightFade, setShowRightFade] = useState(false);

  // Check scroll position to toggle fades
  const updateFades = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    setShowLeftFade(el.scrollLeft > 0);
    setShowRightFade(el.scrollLeft + el.clientWidth < el.scrollWidth - 1);
  }, []);

  // Update fades on mount and resize
  useEffect(() => {
    updateFades();
    window.addEventListener('resize', updateFades);
    return () => window.removeEventListener('resize', updateFades);
  }, [updateFades]);

  // Auto-scroll active tab into view
  useEffect(() => {
    const activeEl = tabRefs.current.get(activeTab);
    if (activeEl) {
      activeEl.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
    }
  }, [activeTab]);

  return (
    <div className="relative">
      {/* Left fade */}
      {showLeftFade && (
        <div className="absolute left-0 top-0 bottom-0 w-8 bg-gradient-to-r from-[var(--color-primary)] to-transparent z-10 pointer-events-none rounded-l-lg" />
      )}

      {/* Scrollable container */}
      <div
        ref={scrollRef}
        onScroll={updateFades}
        className="scroll-container flex flex-nowrap gap-1 bg-secondary-muted/30 rounded-lg p-0.5"
      >
        {tabs.map((tab) => (
          <button
            key={tab.key}
            ref={(el) => {
              if (el) tabRefs.current.set(tab.key, el);
            }}
            onClick={() => onTabChange(tab.key)}
            className={`min-h-[44px] px-4 py-2.5 whitespace-nowrap rounded-md text-sm font-medium transition-colors active:scale-[0.97] ${
              activeTab === tab.key
                ? 'bg-accent text-[#090A3D]'
                : 'text-white/60 hover:text-white active:text-white'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Right fade */}
      {showRightFade && (
        <div className="absolute right-0 top-0 bottom-0 w-8 bg-gradient-to-l from-[var(--color-primary)] to-transparent z-10 pointer-events-none rounded-r-lg" />
      )}
    </div>
  );
}
