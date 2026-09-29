'use client';

import { useState } from 'react';
import { useTrainingTypes } from '@/lib/hooks/useTrainingTypes';

interface TrainingTypeSelectorProps {
  value: string;
  onChange: (value: string) => void;
}

export function TrainingTypeSelector({ value, onChange }: TrainingTypeSelectorProps) {
  const { types, addType } = useTrainingTypes();
  const [showAddInput, setShowAddInput] = useState(false);
  const [newTypeName, setNewTypeName] = useState('');
  const [adding, setAdding] = useState(false);

  async function handleAdd() {
    const name = newTypeName.trim();
    if (!name) return;
    setAdding(true);
    const ok = await addType(name);
    if (ok) {
      onChange(name);
      setNewTypeName('');
      setShowAddInput(false);
    }
    setAdding(false);
  }

  // Ensure current value is in the list (e.g. legacy types)
  const allTypes = types.includes(value) ? types : [...types, value];

  return (
    <div>
      <select
        value={showAddInput ? '__add__' : value}
        onChange={(e) => {
          if (e.target.value === '__add__') {
            setShowAddInput(true);
          } else {
            setShowAddInput(false);
            onChange(e.target.value);
          }
        }}
        className="select w-full"
      >
        {allTypes.map((type) => (
          <option key={type} value={type}>{type}</option>
        ))}
        <option value="__add__">+ Add Type...</option>
      </select>

      {showAddInput && (
        <div className="flex items-center gap-2 mt-2">
          <input
            type="text"
            value={newTypeName}
            onChange={(e) => setNewTypeName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAdd())}
            className="input flex-1 text-sm"
            placeholder="New type name..."
            maxLength={50}
            autoFocus
          />
          <button
            type="button"
            onClick={handleAdd}
            disabled={adding || !newTypeName.trim()}
            className="px-3 py-2 min-h-[36px] rounded text-xs font-medium bg-accent text-[#090A3D] hover:bg-accent/80 disabled:opacity-50 transition-colors"
          >
            {adding ? '...' : 'Add'}
          </button>
          <button
            type="button"
            onClick={() => { setShowAddInput(false); setNewTypeName(''); }}
            className="px-2 py-2 min-h-[36px] rounded text-xs text-white/40 hover:text-white transition-colors"
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}
