'use client';

import { useState } from 'react';
import type { TrainingSession } from '@/lib/types';

interface SessionCalendarProps {
  sessions: TrainingSession[];
  onSelectSession: (session: TrainingSession) => void;
  expandedSessionId: string | null;
}

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

function getTypeColor(trainingType: string): string {
  const t = trainingType.toLowerCase();
  if (t === 'strength') return 'bg-accent/80 text-primary';
  if (t === 'conditioning') return 'bg-amber-500/80 text-primary';
  if (t === 'mobility') return 'bg-green-500/80 text-primary';
  return 'bg-white/20 text-white/80';
}

function getStatusRing(status: TrainingSession['status']): string {
  if (status === 'assigned') return 'ring-1 ring-amber-400';
  if (status === 'completed') return 'ring-1 ring-green-400';
  return '';
}

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

/** Returns 0=Mon .. 6=Sun for the first day of the month */
function getStartDayOfWeek(year: number, month: number): number {
  const day = new Date(year, month, 1).getDay(); // 0=Sun
  return day === 0 ? 6 : day - 1;
}

function formatDateKey(year: number, month: number, day: number): string {
  const m = String(month + 1).padStart(2, '0');
  const d = String(day).padStart(2, '0');
  return `${year}-${m}-${d}`;
}

function isToday(year: number, month: number, day: number): boolean {
  const now = new Date();
  return now.getFullYear() === year && now.getMonth() === month && now.getDate() === day;
}

export function SessionCalendar({ sessions, onSelectSession, expandedSessionId }: SessionCalendarProps) {
  const now = new Date();
  const [currentMonth, setCurrentMonth] = useState(now.getMonth());
  const [currentYear, setCurrentYear] = useState(now.getFullYear());

  const daysInMonth = getDaysInMonth(currentYear, currentMonth);
  const startDay = getStartDayOfWeek(currentYear, currentMonth);

  // Build a map of date string -> sessions for quick lookup
  const sessionsByDate: Record<string, TrainingSession[]> = {};
  for (const session of sessions) {
    const key = session.session_date;
    if (!sessionsByDate[key]) {
      sessionsByDate[key] = [];
    }
    sessionsByDate[key].push(session);
  }

  // Previous month info for leading days
  const prevMonth = currentMonth === 0 ? 11 : currentMonth - 1;
  const prevYear = currentMonth === 0 ? currentYear - 1 : currentYear;
  const daysInPrevMonth = getDaysInMonth(prevYear, prevMonth);

  // Build the grid cells
  const cells: Array<{ day: number; month: number; year: number; isCurrentMonth: boolean }> = [];

  // Leading days from previous month
  for (let i = startDay - 1; i >= 0; i--) {
    cells.push({
      day: daysInPrevMonth - i,
      month: prevMonth,
      year: prevYear,
      isCurrentMonth: false,
    });
  }

  // Current month days
  for (let d = 1; d <= daysInMonth; d++) {
    cells.push({
      day: d,
      month: currentMonth,
      year: currentYear,
      isCurrentMonth: true,
    });
  }

  // Trailing days from next month
  const nextMonth = currentMonth === 11 ? 0 : currentMonth + 1;
  const nextYear = currentMonth === 11 ? currentYear + 1 : currentYear;
  const trailingCount = 7 - (cells.length % 7);
  if (trailingCount < 7) {
    for (let d = 1; d <= trailingCount; d++) {
      cells.push({
        day: d,
        month: nextMonth,
        year: nextYear,
        isCurrentMonth: false,
      });
    }
  }

  const goToPrevMonth = () => {
    if (currentMonth === 0) {
      setCurrentMonth(11);
      setCurrentYear(currentYear - 1);
    } else {
      setCurrentMonth(currentMonth - 1);
    }
  };

  const goToNextMonth = () => {
    if (currentMonth === 11) {
      setCurrentMonth(0);
      setCurrentYear(currentYear + 1);
    } else {
      setCurrentMonth(currentMonth + 1);
    }
  };

  return (
    <div className="w-full">
      {/* Month navigation header */}
      <div className="flex items-center justify-between mb-2">
        <button
          onClick={goToPrevMonth}
          className="min-w-[44px] min-h-[44px] flex items-center justify-center rounded text-white/60 hover:text-white hover:bg-secondary-muted/20 active:scale-[0.97] transition-colors"
          aria-label="Previous month"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12.5 15L7.5 10L12.5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
        <h3 className="font-heading text-sm uppercase tracking-wider text-white">
          {MONTH_NAMES[currentMonth]} {currentYear}
        </h3>
        <button
          onClick={goToNextMonth}
          className="min-w-[44px] min-h-[44px] flex items-center justify-center rounded text-white/60 hover:text-white hover:bg-secondary-muted/20 active:scale-[0.97] transition-colors"
          aria-label="Next month"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M7.5 5L12.5 10L7.5 15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>

      {/* Day of week headers */}
      <div className="grid grid-cols-7 mb-1">
        {DAY_LABELS.map((label) => (
          <div
            key={label}
            className="font-heading text-xs uppercase tracking-wider text-white/40 text-center py-1"
          >
            {label}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className="grid grid-cols-7 border-t border-l border-secondary-muted/30">
        {cells.map((cell, idx) => {
          const dateKey = formatDateKey(cell.year, cell.month, cell.day);
          const daySessions = sessionsByDate[dateKey] || [];
          const today = isToday(cell.year, cell.month, cell.day);

          return (
            <div
              key={idx}
              className={`
                min-h-[40px] border-r border-b border-secondary-muted/30 p-1
                ${cell.isCurrentMonth ? '' : 'opacity-30'}
                ${today ? 'border-2 border-accent' : ''}
              `}
            >
              {/* Day number */}
              <div
                className={`
                  text-xs font-medium mb-0.5 px-0.5
                  ${today ? 'text-accent font-bold' : 'text-white/60'}
                `}
              >
                {cell.day}
              </div>

              {/* Session pills */}
              <div className="flex flex-col gap-0.5">
                {daySessions.map((session) => {
                  const isExpanded = session.id === expandedSessionId;

                  return (
                    <button
                      key={session.id}
                      onClick={() => onSelectSession(session)}
                      className={`
                        w-full text-left px-1 py-0.5 rounded text-[10px] leading-tight font-medium
                        truncate cursor-pointer transition-all
                        ${getTypeColor(session.training_type)}
                        ${getStatusRing(session.status)}
                        ${isExpanded ? 'ring-2 ring-accent scale-[1.02] shadow-lg shadow-accent/20' : 'hover:brightness-110'}
                      `}
                      title={`${session.training_type}${session.status ? ` (${session.status})` : ''}`}
                    >
                      {session.training_type}
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
