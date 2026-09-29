'use client';

import { useState, useEffect, useRef } from 'react';
import { exerciseLibraryApi } from '@/lib/api';
import type { ExerciseLibraryItem } from '@/lib/types';

interface ExerciseAutocompleteProps {
  value: string;
  onChange: (value: string) => void;
  onSelect: (exercise: ExerciseLibraryItem) => void;
  placeholder?: string;
  className?: string;
  categoryFilter?: string;
}

export function ExerciseAutocomplete({
  value,
  onChange,
  onSelect,
  placeholder = 'e.g. Back Squat',
  className = '',
  categoryFilter,
}: ExerciseAutocompleteProps) {
  const [library, setLibrary] = useState<ExerciseLibraryItem[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Load library on first focus
  async function loadLibrary() {
    if (loaded) return;
    try {
      const data = await exerciseLibraryApi.list();
      setLibrary(data);
      setLoaded(true);
    } catch {
      // Silently fail — autocomplete is optional
    }
  }

  // Filter library by current input, with optional category prioritisation
  const textFiltered = library.filter((item) =>
    item.exercise_name.toLowerCase().includes(value.toLowerCase())
  );

  const matchingCategory = categoryFilter
    ? textFiltered.filter((item) => item.exercise_category === categoryFilter)
    : [];
  const otherCategory = categoryFilter
    ? textFiltered.filter((item) => item.exercise_category !== categoryFilter)
    : [];
  const filtered = categoryFilter ? [...matchingCategory, ...otherCategory] : textFiltered;
  const dividerIndex = categoryFilter && matchingCategory.length > 0 && otherCategory.length > 0
    ? matchingCategory.length
    : -1;

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!showDropdown || filtered.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightIndex((prev) => Math.min(prev + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightIndex((prev) => Math.max(prev - 1, 0));
    } else if (e.key === 'Enter' && highlightIndex >= 0) {
      e.preventDefault();
      handleSelect(filtered[highlightIndex]);
    } else if (e.key === 'Escape') {
      setShowDropdown(false);
    }
  }

  function handleSelect(item: ExerciseLibraryItem) {
    onChange(item.exercise_name);
    onSelect(item);
    setShowDropdown(false);
    setHighlightIndex(-1);
  }

  return (
    <div ref={containerRef} className="relative">
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          setShowDropdown(true);
          setHighlightIndex(-1);
        }}
        onFocus={() => {
          loadLibrary();
          setShowDropdown(true);
        }}
        onKeyDown={handleKeyDown}
        className={`input w-full text-sm ${className}`}
        placeholder={placeholder}
        required
        autoComplete="off"
      />

      {showDropdown && filtered.length > 0 && (
        <div className="absolute z-50 top-full left-0 right-0 mt-1 bg-primary-dark border border-secondary-muted rounded-lg shadow-xl max-h-64 overflow-y-auto">
          {filtered.map((item, index) => (
            <div key={item.id}>
              {index === dividerIndex && (
                <div className="px-3 py-1.5 text-[10px] uppercase tracking-wider text-white/30 border-t border-secondary-muted/30">Other</div>
              )}
              <button
                type="button"
                onClick={() => handleSelect(item)}
                className={`w-full text-left px-3 py-3 min-h-[44px] text-sm transition-colors ${
                  index === highlightIndex
                    ? 'bg-accent/20 text-white'
                    : 'text-white/80 hover:bg-white/5 active:bg-accent/20'
                }`}
              >
                <span className="font-medium">{item.exercise_name}</span>
                {item.video_url && (
                  <span
                    role="link"
                    onClick={(e) => { e.stopPropagation(); window.open(item.video_url!, '_blank'); }}
                    className="inline-block ml-1.5 text-accent hover:text-accent/80 cursor-pointer"
                    title="Watch video"
                  >
                    &#9654;
                  </span>
                )}
                {item.exercise_category && (
                  <span className="text-white/40 ml-2 text-xs">{item.exercise_category}</span>
                )}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
