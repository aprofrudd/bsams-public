'use client';

import { useState, useEffect, useCallback } from 'react';
import { trainingBlocksApi } from '@/lib/api';
import { BlockCard } from './BlockCard';
import { BlockBuilderModal } from './BlockBuilderModal';
import { BlockApplyModal } from './BlockApplyModal';
import type { TrainingBlock, TrainingBlockDetail } from '@/lib/types';

export function BlockListView() {
  const [blocks, setBlocks] = useState<TrainingBlock[]>([]);
  const [blockDetails, setBlockDetails] = useState<Record<string, TrainingBlockDetail>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [editingBlock, setEditingBlock] = useState<TrainingBlockDetail | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [applyingBlock, setApplyingBlock] = useState<TrainingBlockDetail | null>(null);

  const loadBlocks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await trainingBlocksApi.list();
      setBlocks(data);
      // Load details for session counts
      const details: Record<string, TrainingBlockDetail> = {};
      await Promise.all(
        data.map(async (block) => {
          try {
            const detail = await trainingBlocksApi.get(block.id);
            details[block.id] = detail;
          } catch {
            // Silently skip detail load failures
          }
        })
      );
      setBlockDetails(details);
    } catch {
      setError('Failed to load training blocks');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadBlocks();
  }, [loadBlocks]);

  async function handleDelete(blockId: string) {
    if (!window.confirm('Delete this training block? This cannot be undone.')) return;
    try {
      await trainingBlocksApi.delete(blockId);
      setBlocks(prev => prev.filter(b => b.id !== blockId));
    } catch {
      setError('Failed to delete block');
    }
  }

  async function handleEdit(blockId: string) {
    try {
      const detail = blockDetails[blockId] || await trainingBlocksApi.get(blockId);
      setEditingBlock(detail);
    } catch {
      setError('Failed to load block');
    }
  }

  async function handleApply(blockId: string) {
    try {
      const detail = blockDetails[blockId] || await trainingBlocksApi.get(blockId);
      setApplyingBlock(detail);
    } catch {
      setError('Failed to load block');
    }
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-white/60">Your training blocks</p>
        <button
          onClick={() => { setEditingBlock(null); setShowCreateModal(true); }}
          className="px-4 py-2 min-h-[44px] rounded text-sm font-medium bg-accent text-[#090A3D] hover:bg-accent/80 transition-colors"
        >
          + New Block
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-sm text-red-400 mb-4">
          {error}
          <button onClick={() => setError(null)} className="ml-2 text-red-300 hover:text-red-200">&times;</button>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
      ) : blocks.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-white/60 text-sm mb-2">No training blocks yet.</p>
          <p className="text-white/40 text-xs">
            Create a block to define multi-week training programs and apply them to your athletes.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {blocks.map(block => (
            <BlockCard
              key={block.id}
              block={block}
              sessionCount={blockDetails[block.id]?.sessions?.length ?? 0}
              onEdit={() => handleEdit(block.id)}
              onDelete={() => handleDelete(block.id)}
              onApply={() => handleApply(block.id)}
            />
          ))}
        </div>
      )}

      {(showCreateModal || editingBlock) && (
        <BlockBuilderModal
          existingBlock={editingBlock}
          onClose={() => { setShowCreateModal(false); setEditingBlock(null); }}
          onSaved={() => { setShowCreateModal(false); setEditingBlock(null); loadBlocks(); }}
        />
      )}

      {applyingBlock && (
        <BlockApplyModal
          block={applyingBlock}
          onClose={() => setApplyingBlock(null)}
          onApplied={() => { setApplyingBlock(null); }}
        />
      )}
    </div>
  );
}
