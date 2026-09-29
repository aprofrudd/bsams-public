'use client';

import type { TrainingBlock } from '@/lib/types';

interface BlockCardProps {
  block: TrainingBlock;
  sessionCount: number;
  onEdit: () => void;
  onDelete: () => void;
  onApply: () => void;
}

export function BlockCard({ block, sessionCount, onEdit, onDelete, onApply }: BlockCardProps) {
  return (
    <div className="border border-secondary-muted rounded-lg p-4 hover:border-accent/30 transition-colors">
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1 min-w-0">
          <h3 className="font-medium text-sm truncate">{block.block_name}</h3>
          <div className="flex items-center gap-2 mt-1">
            <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-accent/10 text-accent">
              {block.category}
            </span>
            <span className="text-xs text-white/40">
              {block.num_weeks} week{block.num_weeks !== 1 ? 's' : ''}
            </span>
            <span className="text-xs text-white/40">
              {sessionCount} session{sessionCount !== 1 ? 's' : ''}
            </span>
          </div>
        </div>
      </div>

      {block.description && (
        <p className="text-xs text-white/50 mb-3 line-clamp-2">{block.description}</p>
      )}

      <div className="flex items-center gap-2">
        <button
          onClick={onApply}
          className="px-3 py-1.5 min-h-[44px] rounded text-xs font-medium bg-accent text-[#090A3D] hover:bg-accent/80 transition-colors flex-1"
        >
          Apply to Athletes
        </button>
        <button
          onClick={onEdit}
          className="px-3 py-1.5 min-h-[44px] rounded text-xs font-medium bg-white/5 text-white/60 hover:bg-white/10 transition-colors"
        >
          Edit
        </button>
        <button
          onClick={onDelete}
          className="px-3 py-1.5 min-h-[44px] rounded text-xs font-medium bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
        >
          Delete
        </button>
      </div>
    </div>
  );
}
