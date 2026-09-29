'use client';

import { useState, useEffect, useRef } from 'react';

interface SessionActionMenuProps {
  canComplete: boolean;
  canDelete: boolean;
  isCoachOrAdmin: boolean;
  canManageExercises?: boolean;
  showTimer?: boolean;
  completeLabel?: string;
  onComplete: () => void;
  onAddExercise: () => void;
  onTemplate: () => void;
  onEditExercises?: () => void;
  onTimer: () => void;
  onDelete: () => void;
}

export function SessionActionMenu({
  canComplete, canDelete, isCoachOrAdmin, canManageExercises, showTimer, completeLabel,
  onComplete, onAddExercise, onTemplate, onEditExercises, onTimer, onDelete,
}: SessionActionMenuProps) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function handleEscape(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [open]);

  function fire(action: () => void) {
    setOpen(false);
    action();
  }

  const manage = canManageExercises ?? isCoachOrAdmin;
  const items: { label: string; action: () => void; color: string; show: boolean }[] = [
    { label: completeLabel || 'Complete', action: onComplete, color: 'text-accent', show: canComplete },
    { label: '+ Exercise', action: onAddExercise, color: 'text-white/80', show: manage },
    { label: 'Template', action: onTemplate, color: 'text-white/80', show: manage },
    { label: 'Edit Exercises', action: onEditExercises || (() => {}), color: 'text-white/80', show: manage && !!onEditExercises },
    { label: 'Timer', action: onTimer, color: 'text-white/80', show: !!showTimer },
    { label: 'Delete', action: onDelete, color: 'text-red-400', show: canDelete },
  ];

  const visibleItems = items.filter(i => i.show);
  if (visibleItems.length === 0) return null;

  return (
    <div ref={menuRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center justify-center w-[44px] h-[44px] rounded text-white/60 hover:text-white hover:bg-white/10 active:scale-[0.97] transition-colors"
        aria-label="Session actions"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
          <path d="M10 3a1.5 1.5 0 110 3 1.5 1.5 0 010-3zM10 8.5a1.5 1.5 0 110 3 1.5 1.5 0 010-3zM11.5 15.5a1.5 1.5 0 10-3 0 1.5 1.5 0 003 0z" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-48 z-40 bg-[#0c0e42] border border-secondary-muted/30 rounded-lg shadow-2xl shadow-black/50 overflow-hidden">
          {visibleItems.map((item) => (
            <button
              key={item.label}
              type="button"
              onClick={() => fire(item.action)}
              className={`w-full text-left min-h-[44px] px-4 py-3 text-sm font-medium ${item.color} hover:bg-white/5 active:bg-white/10 transition-colors`}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
