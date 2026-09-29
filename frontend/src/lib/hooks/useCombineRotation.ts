'use client';

import { useEffect, useState } from 'react';

/**
 * Cycles the kiosk through its panels.
 *
 * Skips panels with nothing on them — at 09:00 the room has no data and an empty
 * board is worse than a shorter rotation — but always keeps at least one so the
 * screen is never blank.
 */
export function useCombineRotation(
  panels: string[],
  options?: { intervalMs?: number; pinned?: string | null; paused?: boolean }
) {
  const { intervalMs = 20000, pinned = null, paused = false } = options ?? {};
  const [index, setIndex] = useState(0);

  const total = panels.length;
  // A panel is only really pinned when it is one of the panels on offer. A screen
  // left on ?panel=landmine before that station has logged anything must keep
  // rotating, not sit on a panel there is nothing to draw.
  const pinnedIndex = pinned ? panels.indexOf(pinned) : -1;
  const isPinned = pinnedIndex >= 0;

  useEffect(() => {
    if (isPinned || paused || total <= 1) return;
    const id = setInterval(() => {
      if (typeof document !== 'undefined' && document.hidden) return;
      setIndex((current) => (current + 1) % total);
    }, intervalMs);
    return () => clearInterval(id);
  }, [isPinned, paused, total, intervalMs]);

  // Keep the index in range when panels appear or disappear mid-event.
  useEffect(() => {
    setIndex((current) => (total === 0 ? 0 : current % total));
  }, [total]);

  // While a panel is pinned the cursor follows it, so releasing the pin carries on
  // from the panel on screen rather than snapping back to wherever the rotation had
  // got to before it was pinned.
  useEffect(() => {
    if (isPinned) setIndex(pinnedIndex);
  }, [isPinned, pinnedIndex]);

  const active = isPinned ? panels[pinnedIndex] : panels[index % Math.max(total, 1)];

  return {
    active: active ?? null,
    index: isPinned ? pinnedIndex : index,
    total,
    isPinned,
    next: () => setIndex((current) => (current + 1) % Math.max(total, 1)),
    previous: () => setIndex((current) => (current - 1 + total) % Math.max(total, 1)),
  };
}
