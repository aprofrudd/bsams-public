'use client';

import { useState, useEffect, useCallback, useMemo, Fragment } from 'react';
import { exercisesApi } from '@/lib/api';
import { ExerciseAutocomplete } from './ExerciseAutocomplete';
import { TemplatePickerModal } from './TemplatePickerModal';
import { ConditioningExerciseForm } from './ConditioningExerciseForm';
import { CircuitExerciseForm } from './CircuitExerciseForm';
import { StepperInput } from './StepperInput';
import type { ExercisePrescription, ExerciseLibraryItem } from '@/lib/types';

interface ExerciseTableProps {
  sessionId: string;
  trainingType?: string;
  readOnly?: boolean;
  autoShowAddForm?: boolean;
  onAddFormShown?: () => void;
  autoShowTemplatePicker?: boolean;
  onTemplatePickerShown?: () => void;
  autoEdit?: boolean;
  onAutoEditDone?: () => void;
}

interface ExerciseGroup {
  exerciseName: string;
  category: string | null;
  exercises: ExercisePrescription[];
  uniformReps: boolean;
  uniformWeight: boolean;
  summaryReps: number | null;
  summaryWeight: number | null;
  summaryRest: number | null;
  summaryDuration: number | null;
  summaryIntensityType: string | null;
  summaryIntensityValue: number | null;
  summaryIntensityMin: number | null;
  summaryIntensityMax: number | null;
}

const EXERCISE_CATEGORIES = ['Strength', 'Plyometric', 'Conditioning', 'Circuit', 'Other'];

const SECTION_LABELS: Record<string, string> = {
  hand_prep: 'HAND PREP',
  extended_warmup: 'EXTENDED WARM-UP',
  superset_1: 'SUPERSET 1',
  superset_2: 'SUPERSET 2',
  superset_3: 'SUPERSET 3',
  core_circuit: 'CORE CIRCUIT',
  perform_separate: 'PERFORM SEPARATE',
};

interface SectionGroup {
  sectionType: string;
  label: string;
  groups: ExerciseGroup[];
}

function groupBySection(exercises: ExercisePrescription[]): SectionGroup[] | null {
  const hasSections = exercises.some((ex) => ex.section_type);
  if (!hasSections) return null;

  const sectionMap = new Map<string, ExercisePrescription[]>();
  const sectionOrder: string[] = [];
  for (const ex of exercises) {
    const key = ex.section_type || '__none__';
    if (!sectionMap.has(key)) {
      sectionMap.set(key, []);
      sectionOrder.push(key);
    }
    sectionMap.get(key)!.push(ex);
  }

  return sectionOrder.map((key) => ({
    sectionType: key,
    label: SECTION_LABELS[key] || key.toUpperCase(),
    groups: groupExercises(sectionMap.get(key)!),
  }));
}

function groupExercises(exercises: ExercisePrescription[]): ExerciseGroup[] {
  // Separate circuit exercises into a single group
  const circuitExercises = exercises
    .filter(ex => ex.exercise_category?.toLowerCase() === 'circuit')
    .sort((a, b) => a.set_number - b.set_number);
  const nonCircuitExercises = exercises
    .filter(ex => ex.exercise_category?.toLowerCase() !== 'circuit');

  const groupMap = new Map<string, ExercisePrescription[]>();
  const groupOrder: string[] = [];

  for (const ex of nonCircuitExercises) {
    const key = ex.exercise_name;
    if (!groupMap.has(key)) {
      groupMap.set(key, []);
      groupOrder.push(key);
    }
    groupMap.get(key)!.push(ex);
  }

  const groups: ExerciseGroup[] = groupOrder.map((name) => {
    const exs = groupMap.get(name)!;
    exs.sort((a, b) => a.set_number - b.set_number);

    const repsValues = exs.map((e) => e.reps);
    const weightValues = exs.map((e) => e.weight_kg);
    const uniformReps = repsValues.every((v) => v === repsValues[0]);
    const uniformWeight = weightValues.every((v) => v === weightValues[0]);

    return {
      exerciseName: name,
      category: exs[0].exercise_category,
      exercises: exs,
      uniformReps,
      uniformWeight,
      summaryReps: uniformReps ? repsValues[0] : null,
      summaryWeight: uniformWeight ? weightValues[0] : null,
      summaryRest: exs[0].rest_seconds,
      summaryDuration: exs[0].duration_seconds,
      summaryIntensityType: exs[0].intensity_type,
      summaryIntensityValue: exs[0].intensity_value,
      summaryIntensityMin: exs[0].intensity_min,
      summaryIntensityMax: exs[0].intensity_max,
    };
  });

  // Add circuit as a single group if present
  if (circuitExercises.length > 0) {
    groups.push({
      exerciseName: '__circuit__',
      category: 'Circuit',
      exercises: circuitExercises,
      uniformReps: false,
      uniformWeight: false,
      summaryReps: null,
      summaryWeight: null,
      summaryRest: null,
      summaryDuration: circuitExercises[0].duration_seconds,
      summaryIntensityType: null,
      summaryIntensityValue: null,
      summaryIntensityMin: null,
      summaryIntensityMax: null,
    });
  }

  return groups;
}

function formatDuration(ex: ExercisePrescription): string {
  if (ex.rep_durations) return ex.rep_durations.join('/') + 's';
  if (ex.duration_seconds != null) return `${ex.duration_seconds}s`;
  return '-';
}

function isConditioningGroup(group: ExerciseGroup): boolean {
  return group.category?.toLowerCase() === 'conditioning';
}

function isCircuitGroup(group: ExerciseGroup): boolean {
  return group.category?.toLowerCase() === 'circuit';
}

/** Get unique exercise count and round count from interleaved circuit prescriptions. */
function getCircuitInfo(exercises: ExercisePrescription[]) {
  const seen = new Set<string>();
  const order: string[] = [];
  for (const ex of exercises) {
    if (!seen.has(ex.exercise_name)) {
      seen.add(ex.exercise_name);
      order.push(ex.exercise_name);
    }
  }
  const uniqueCount = order.length;
  const rounds = uniqueCount > 0 ? Math.round(exercises.length / uniqueCount) : 0;
  return { uniqueCount, rounds, exerciseNames: order };
}

export function ExerciseTable({ sessionId, trainingType, readOnly, autoShowAddForm, onAddFormShown, autoShowTemplatePicker, onTemplatePickerShown, autoEdit, onAutoEditDone }: ExerciseTableProps) {
  const isConditioning = trainingType === 'Conditioning';
  const isCircuit = trainingType === 'Circuit';
  const [exercises, setExercises] = useState<ExercisePrescription[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New exercise form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [exerciseName, setExerciseName] = useState('');
  const [category, setCategory] = useState(() => {
    if (trainingType === 'Conditioning') return 'Conditioning';
    if (trainingType === 'Circuit') return 'Circuit';
    if (trainingType === 'Plyometric') return 'Plyometric';
    return 'Strength';
  });
  const [showCategoryDropdown, setShowCategoryDropdown] = useState(false);
  const [numberOfSets, setNumberOfSets] = useState(1);

  interface SetConfig {
    reps: string;
    weight_kg: string;
  }
  const [setConfigs, setSetConfigs] = useState<SetConfig[]>([{ reps: '', weight_kg: '' }]);
  const [restBetweenSetsArr, setRestBetweenSetsArr] = useState<string[]>([]);

  const [intensityType, setIntensityType] = useState('');
  const [intensityValue, setIntensityValue] = useState('');
  const [restBetweenReps, setRestBetweenReps] = useState('');
  const [durationSeconds, setDurationSeconds] = useState('');
  const [saving, setSaving] = useState(false);

  function selectOnFocus(e: React.FocusEvent<HTMLInputElement>) {
    e.target.select();
  }

  function handleSetCount(count: number) {
    setNumberOfSets(count);
    setSetConfigs(prev => {
      if (count > prev.length) {
        const last = prev[prev.length - 1];
        return [...prev, ...Array.from({ length: count - prev.length }, () => ({ ...last }))];
      }
      return prev.slice(0, count);
    });
    setRestBetweenSetsArr(prev => {
      const needed = count - 1;
      if (needed > prev.length) {
        return [...prev, ...Array.from({ length: needed - prev.length }, () => '')];
      }
      return prev.slice(0, needed);
    });
  }

  // Template picker state
  const [showTemplatePicker, setShowTemplatePicker] = useState(false);

  // Group expand/collapse state
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  // Conditioning edit state
  const [editingGroupName, setEditingGroupName] = useState<string | null>(null);

  // Inline edit state: track modified reps/weight per exercise
  const [editedValues, setEditedValues] = useState<Record<string, { reps?: string; weight_kg?: string }>>({});
  const [savingEdits, setSavingEdits] = useState(false);

  const hasEdits = Object.keys(editedValues).length > 0;

  const groups = useMemo(() => groupExercises(exercises), [exercises]);
  const sectionGroups = useMemo(() => groupBySection(exercises), [exercises]);

  function toggleGroup(exerciseName: string) {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(exerciseName)) {
        next.delete(exerciseName);
      } else {
        next.add(exerciseName);
      }
      return next;
    });
  }

  const loadExercises = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await exercisesApi.list(sessionId);
      setExercises(data);
      setEditedValues({});
    } catch (err) {
      setError('Failed to load exercises');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    loadExercises();
  }, [loadExercises]);

  // Auto-trigger add form or template picker from parent
  useEffect(() => {
    if (autoShowAddForm) {
      setShowAddForm(true);
      onAddFormShown?.();
    }
  }, [autoShowAddForm, onAddFormShown]);

  useEffect(() => {
    if (autoShowTemplatePicker) {
      setShowTemplatePicker(true);
      onTemplatePickerShown?.();
    }
  }, [autoShowTemplatePicker, onTemplatePickerShown]);

  // Auto-edit: expand all groups when triggered
  useEffect(() => {
    if (autoEdit && groups.length > 0) {
      setExpandedGroups(new Set(groups.map(g => g.exerciseName)));
      onAutoEditDone?.();
    }
  }, [autoEdit, groups, onAutoEditDone]);

  function handleLibrarySelect(item: ExerciseLibraryItem) {
    setExerciseName(item.exercise_name);
    if (item.exercise_category) setCategory(item.exercise_category);
    if (item.default_set_configs && item.default_set_configs.length > 0) {
      const configs = item.default_set_configs;
      handleSetCount(configs.length);
      setSetConfigs(configs.map(c => ({
        reps: c.reps != null ? String(c.reps) : '',
        weight_kg: c.weight_kg != null ? String(c.weight_kg) : '',
      })));
    } else if (item.default_reps || item.default_weight_kg) {
      setSetConfigs(prev => prev.map(s => ({
        reps: item.default_reps ? String(item.default_reps) : s.reps,
        weight_kg: item.default_weight_kg ? String(item.default_weight_kg) : s.weight_kg,
      })));
    }
    if (item.default_intensity_type) setIntensityType(item.default_intensity_type);
    if (item.default_intensity_value) setIntensityValue(String(item.default_intensity_value));
    if (item.default_rest_between_reps_seconds) setRestBetweenReps(String(item.default_rest_between_reps_seconds));
    if (item.default_duration_seconds) setDurationSeconds(String(item.default_duration_seconds));
  }

  async function handleAddExercise(e: React.FormEvent) {
    e.preventDefault();
    if (!exerciseName.trim()) return;

    setSaving(true);
    try {
      const nextSetNumber = (exercises.length > 0 ? Math.max(...exercises.map(e => e.set_number)) : 0) + 1;
      for (let i = 0; i < setConfigs.length; i++) {
        const sc = setConfigs[i];
        await exercisesApi.create(sessionId, {
          exercise_name: exerciseName.trim(),
          exercise_category: category,
          set_number: nextSetNumber + i,
          reps: sc.reps ? Number(sc.reps) : undefined,
          weight_kg: sc.weight_kg ? Number(sc.weight_kg) : undefined,
          intensity_type: intensityType || undefined,
          intensity_value: intensityValue ? Number(intensityValue) : undefined,
          rest_between_reps_seconds: restBetweenReps ? Number(restBetweenReps) : undefined,
          duration_seconds: durationSeconds ? Number(durationSeconds) : undefined,
          rest_seconds: i < restBetweenSetsArr.length && restBetweenSetsArr[i]
            ? Number(restBetweenSetsArr[i]) : undefined,
        });
      }
      // Reset form
      setExerciseName('');
      setNumberOfSets(1);
      setSetConfigs([{ reps: '', weight_kg: '' }]);
      setRestBetweenSetsArr([]);
      setIntensityType('');
      setIntensityValue('');
      setRestBetweenReps('');
      setDurationSeconds('');
      setShowAddForm(false);
      setShowCategoryDropdown(false);
      loadExercises();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add exercise');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(exerciseId: string) {
    try {
      await exercisesApi.delete(sessionId, exerciseId);
      setExercises((prev) => prev.filter((ex) => ex.id !== exerciseId));
    } catch (err) {
      console.error('Failed to delete exercise:', err);
    }
  }

  async function handleDeleteGroup(group: ExerciseGroup) {
    try {
      for (const ex of group.exercises) {
        await exercisesApi.delete(sessionId, ex.id);
      }
      setExercises((prev) => prev.filter((ex) => ex.exercise_name !== group.exerciseName));
      setExpandedGroups((prev) => {
        const next = new Set(prev);
        next.delete(group.exerciseName);
        return next;
      });
    } catch (err) {
      console.error('Failed to delete exercise group:', err);
    }
  }

  function handleInlineEdit(exerciseId: string, field: 'reps' | 'weight_kg', value: string) {
    setEditedValues((prev) => {
      const existing = prev[exerciseId] || {};
      const updated = { ...existing, [field]: value };
      // Check if value matches the original — if so, remove that field
      const original = exercises.find((ex) => ex.id === exerciseId);
      if (original) {
        const origVal = field === 'reps'
          ? (original.reps != null ? String(original.reps) : '')
          : (original.weight_kg != null ? String(original.weight_kg) : '');
        if (value === origVal) {
          delete updated[field];
        }
      }
      // If no fields remain, remove the exercise entry
      if (Object.keys(updated).length === 0) {
        const { [exerciseId]: _, ...rest } = prev;
        return rest;
      }
      return { ...prev, [exerciseId]: updated };
    });
  }

  /** Auto-save a single field on blur (coach inline editing) */
  async function handleInlineBlurSave(exerciseId: string, field: 'reps' | 'weight_kg') {
    const edited = editedValues[exerciseId];
    if (!edited || edited[field] === undefined) return;

    const value = edited[field]!;
    const updateData: Record<string, number | undefined> = {};
    updateData[field] = value ? Number(value) : undefined;

    try {
      await exercisesApi.update(sessionId, exerciseId, updateData);
      // Clear this edit entry on success
      setEditedValues((prev) => {
        const entry = { ...prev[exerciseId] };
        delete entry[field];
        if (Object.keys(entry).length === 0) {
          const { [exerciseId]: _, ...rest } = prev;
          return rest;
        }
        return { ...prev, [exerciseId]: entry };
      });
      // Update the local exercises state with new value
      setExercises((prev) => prev.map((ex) => {
        if (ex.id !== exerciseId) return ex;
        return { ...ex, [field]: value ? Number(value) : null };
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save');
    }
  }

  async function handleSaveEdits() {
    setSavingEdits(true);
    setError(null);
    try {
      for (const [exerciseId, changes] of Object.entries(editedValues)) {
        const updateData: Record<string, number | undefined> = {};
        if (changes.reps !== undefined) updateData.reps = changes.reps ? Number(changes.reps) : undefined;
        if (changes.weight_kg !== undefined) updateData.weight_kg = changes.weight_kg ? Number(changes.weight_kg) : undefined;
        await exercisesApi.update(sessionId, exerciseId, updateData);
      }
      await loadExercises();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save changes');
    } finally {
      setSavingEdits(false);
    }
  }

  const [addingSetGroup, setAddingSetGroup] = useState<string | null>(null);

  async function handleAddSet(group: ExerciseGroup) {
    setAddingSetGroup(group.exerciseName);
    try {
      const lastEx = group.exercises[group.exercises.length - 1];
      const maxSetNumber = Math.max(...group.exercises.map(e => e.set_number));
      await exercisesApi.create(sessionId, {
        exercise_name: group.exerciseName,
        exercise_category: lastEx.exercise_category ?? undefined,
        set_number: maxSetNumber + 1,
        reps: lastEx.reps ?? undefined,
        weight_kg: lastEx.weight_kg ?? undefined,
        rest_seconds: lastEx.rest_seconds ?? undefined,
        duration_seconds: lastEx.duration_seconds ?? undefined,
        intensity_type: lastEx.intensity_type ?? undefined,
        intensity_value: lastEx.intensity_value ?? undefined,
        rest_between_reps_seconds: lastEx.rest_between_reps_seconds ?? undefined,
      });
      await loadExercises();
      // Ensure group is expanded to show the new set
      setExpandedGroups((prev) => new Set(prev).add(group.exerciseName));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add set');
    } finally {
      setAddingSetGroup(null);
    }
  }

  function getDisplayValue(ex: ExercisePrescription, field: 'reps' | 'weight_kg'): string {
    const edited = editedValues[ex.id];
    if (edited && edited[field] !== undefined) return edited[field]!;
    const val = field === 'reps' ? ex.reps : ex.weight_kg;
    return val != null ? String(val) : '';
  }

  function formatIntensity(ex: ExercisePrescription): string {
    if (!ex.intensity_type) return '';
    const unit = ex.intensity_type === 'rpe' ? 'RPE ' : ex.intensity_type === 'speed_kmh' ? '' : '';
    const suffix = ex.intensity_type === 'speed_kmh' ? ' km/h' : ex.intensity_type === 'power_watts' ? 'W' : '';
    if (ex.rep_intensity_values && ex.rep_intensity_values.length > 0) {
      const allSame = ex.rep_intensity_values.every(v => v === ex.rep_intensity_values![0]);
      if (allSame) return `${unit}${ex.rep_intensity_values[0]}${suffix}`;
      return `${unit}${ex.rep_intensity_values.join('/')}${suffix}`;
    }
    if (ex.intensity_value != null) {
      return `${unit}${ex.intensity_value}${suffix}`;
    }
    return '';
  }

  function formatGroupIntensity(group: ExerciseGroup): string {
    if (!group.summaryIntensityType) return '';
    // Show range if both min and max are set
    if (group.summaryIntensityMin != null && group.summaryIntensityMax != null) {
      if (group.summaryIntensityType === 'rpe') return `RPE ${group.summaryIntensityMin}-${group.summaryIntensityMax}`;
      if (group.summaryIntensityType === 'speed_kmh') return `${group.summaryIntensityMin}-${group.summaryIntensityMax} km/h`;
      return `${Math.round(group.summaryIntensityMin)}-${Math.round(group.summaryIntensityMax)}W`;
    }
    // Fall back to single value
    if (group.summaryIntensityValue == null) return '';
    if (group.summaryIntensityType === 'rpe') return `RPE ${group.summaryIntensityValue}`;
    if (group.summaryIntensityType === 'speed_kmh') return `${group.summaryIntensityValue} km/h`;
    return `${group.summaryIntensityValue}W`;
  }

  return (
    <div className="mt-3 border-t border-secondary-muted/50 pt-3">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-xs font-medium text-white/60 uppercase tracking-wider">Exercises</h4>
      </div>

      {loading ? (
        <div className="text-center py-4">
          <div className="inline-block w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
      ) : error ? (
        <p className="text-red-400 text-sm py-2 text-center">{error}</p>
      ) : exercises.length === 0 && !showAddForm ? (
        <p className="text-white/40 text-xs py-2 text-center">
          No exercises logged
        </p>
      ) : (
        <div className="overflow-x-auto mb-3">
          <table className="w-full text-sm">
            <tbody>
              {(sectionGroups || [{ sectionType: '__all__', label: '', groups }]).map((section) => (
                <Fragment key={section.sectionType}>
                  {/* Section header (only for programme-form sessions with section_type) */}
                  {section.sectionType !== '__all__' && (
                    <tr>
                      <td colSpan={readOnly ? 5 : 6} className="pt-3 pb-1 px-2">
                        <span className="text-xs font-bold tracking-wider text-accent">
                          {section.label}
                        </span>
                      </td>
                    </tr>
                  )}
                  {section.groups.map((group) => {
                const isExpanded = readOnly || expandedGroups.has(group.exerciseName);
                const setCount = group.exercises.length;
                const isCond = isConditioningGroup(group);
                const isCirc = isCircuitGroup(group);
                const isEditingGroup = editingGroupName === group.exerciseName;
                const circuitInfo = isCirc ? getCircuitInfo(group.exercises) : null;
                const hasRepsText = group.exercises.some((ex) => ex.reps_text);
                const hasRecWeight = group.exercises.some((ex) => ex.recommended_weight_kg != null);

                return (
                  <Fragment key={`${section.sectionType}-${group.exerciseName}`}>
                    {/* Summary row */}
                    <tr
                      className="border-b border-secondary-muted/30 hover:bg-secondary-muted/10 transition-colors cursor-pointer"
                      onClick={() => !readOnly && toggleGroup(group.exerciseName)}
                    >
                      {/* Chevron (coaches only) */}
                      <td className="py-1.5 px-1 text-center w-8">
                        {!readOnly && (
                          <span
                            className="inline-block text-white/40 text-xs transition-transform duration-150"
                            style={{ transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)' }}
                          >
                            &#9654;
                          </span>
                        )}
                      </td>

                      {/* Exercise name + inline category */}
                      <td className="py-1.5 px-2 font-medium">
                        {isCirc ? 'Circuit' : group.exerciseName}
                        {group.category && !isCirc && (
                          <span className="ml-2 text-[10px] font-normal text-white/30 uppercase">
                            {group.category}
                          </span>
                        )}
                      </td>

                      {isCirc && circuitInfo ? (
                        <>
                          {/* Circuit: exercises x rounds */}
                          <td className="py-1.5 px-2 text-right text-white/60">
                            {circuitInfo.uniqueCount} exercises x {circuitInfo.rounds} rounds
                          </td>
                          <td className="py-1.5 px-2 text-right text-white/60 hidden sm:table-cell">
                            {group.exercises[0]?.duration_seconds != null ? `${group.exercises[0].duration_seconds}s work` : ''}
                          </td>
                        </>
                      ) : isCond ? (
                        <>
                          {/* Conditioning: sets, duration, intensity */}
                          <td className="py-1.5 px-2 text-right text-white/60">
                            {setCount} {setCount === 1 ? 'set' : 'sets'}
                          </td>
                          <td className="py-1.5 px-2 text-right text-white/60 hidden sm:table-cell">
                            {formatDuration(group.exercises[0])}
                          </td>
                          <td className="py-1.5 px-2 text-white/60 hidden sm:table-cell">
                            {formatGroupIntensity(group)}
                          </td>
                        </>
                      ) : hasRepsText ? (
                        <>
                          {/* Programme form: reps_text display */}
                          <td className="py-1.5 px-2 text-right text-white/60">
                            {group.exercises[0]?.reps_text || `${setCount} sets`}
                          </td>
                          <td className="py-1.5 px-2 text-right text-white/60">
                            {group.uniformWeight
                              ? (group.summaryWeight != null ? `${group.summaryWeight}kg` : '')
                              : <span className="text-white/40 italic">varies</span>}
                            {hasRecWeight && group.exercises[0]?.recommended_weight_kg != null && (
                              <span className="ml-1 text-[10px] text-accent">
                                Rec: {group.exercises[0].recommended_weight_kg}kg
                              </span>
                            )}
                          </td>
                        </>
                      ) : (
                        <>
                          {/* Strength: sets x reps, weight */}
                          <td className="py-1.5 px-2 text-right text-white/60">
                            {group.uniformReps && group.summaryReps != null
                              ? `${setCount} x ${group.summaryReps}`
                              : `${setCount} sets, varies`}
                          </td>
                          <td className="py-1.5 px-2 text-right text-white/60">
                            {group.uniformWeight
                              ? (group.summaryWeight != null ? `${group.summaryWeight}kg` : '')
                              : <span className="text-white/40 italic">varies</span>}
                            {hasRecWeight && group.exercises[0]?.recommended_weight_kg != null && (
                              <span className="ml-1 text-[10px] text-accent">
                                Rec: {group.exercises[0].recommended_weight_kg}kg
                              </span>
                            )}
                          </td>
                        </>
                      )}

                      {/* Action buttons (coaches only) */}
                      {!readOnly && (
                        <td className="py-1.5 px-2 text-right whitespace-nowrap">
                          {(isCond || isCirc) && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setEditingGroupName(isEditingGroup ? null : group.exerciseName);
                              }}
                              className="px-2 py-1 min-h-[36px] text-xs rounded text-accent hover:bg-accent/10 active:scale-[0.97] transition-colors"
                            >
                              {isEditingGroup ? 'Cancel' : 'Edit'}
                            </button>
                          )}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteGroup(group);
                            }}
                            className="px-2 py-1 min-h-[36px] text-xs rounded text-white/40 hover:text-red-400 hover:bg-red-400/10 active:scale-[0.97] transition-colors"
                          >
                            Delete
                          </button>
                        </td>
                      )}
                    </tr>

                    {/* Conditioning edit form (inline below summary) */}
                    {!readOnly && isCond && isEditingGroup && (
                      <tr>
                        <td colSpan={readOnly ? 5 : 6} className="p-3 bg-secondary-muted/5 border-b border-secondary-muted/20">
                          <ConditioningExerciseForm
                            sessionId={sessionId}
                            nextSetNumber={0}
                            existingExercises={group.exercises}
                            onSaved={() => {
                              setEditingGroupName(null);
                              loadExercises();
                            }}
                            onCancel={() => setEditingGroupName(null)}
                          />
                        </td>
                      </tr>
                    )}

                    {/* Circuit edit form (inline below summary) */}
                    {!readOnly && isCirc && isEditingGroup && (
                      <tr>
                        <td colSpan={readOnly ? 4 : 5} className="p-3 bg-secondary-muted/5 border-b border-secondary-muted/20">
                          <CircuitExerciseForm
                            sessionId={sessionId}
                            nextSetNumber={0}
                            existingExercises={group.exercises}
                            onSaved={() => {
                              setEditingGroupName(null);
                              loadExercises();
                            }}
                            onCancel={() => setEditingGroupName(null)}
                          />
                        </td>
                      </tr>
                    )}

                    {/* Expanded individual set rows */}
                    {isExpanded && !isEditingGroup && !isCirc && group.exercises.map((ex) => (
                      <tr
                        key={ex.id}
                        className="border-b border-secondary-muted/20 bg-secondary-muted/5"
                      >
                        <td className="py-1.5 px-1"></td>
                        <td className="py-1.5 px-2 pl-6 text-white/50 text-xs">
                          Set {ex.set_number}
                          {ex.reps_text && (
                            <span className="ml-2 text-white/40">{ex.reps_text}</span>
                          )}
                        </td>

                        {isCond ? (
                          <>
                            {/* Conditioning set: duration, intensity */}
                            <td className="py-1.5 px-2 text-right text-white/50">
                              {formatDuration(ex)}
                            </td>
                            <td className="py-1.5 px-2 text-white/50 hidden sm:table-cell">
                              {ex.rest_seconds != null ? `${ex.rest_seconds}s rest` : ''}
                            </td>
                            <td className="py-1.5 px-2 text-white/50 hidden sm:table-cell">
                              {formatIntensity(ex)}
                            </td>
                          </>
                        ) : (
                          <>
                            {/* Strength set: reps, weight (editable) */}
                            <td className="py-1.5 px-2 text-right">
                              <input
                                type="number"
                                min="0"
                                max="100"
                                value={getDisplayValue(ex, 'reps')}
                                onChange={(e) => handleInlineEdit(ex.id, 'reps', e.target.value)}
                                onBlur={!readOnly ? () => handleInlineBlurSave(ex.id, 'reps') : undefined}
                                className="input w-16 text-sm text-right py-1 px-1.5"
                                placeholder="-"
                              />
                            </td>
                            <td className="py-1.5 px-2 text-right">
                              <div className="flex items-center justify-end gap-1">
                                {ex.recommended_weight_kg != null && (
                                  <span className="text-[10px] text-accent whitespace-nowrap">
                                    Rec: {ex.recommended_weight_kg}kg
                                  </span>
                                )}
                                <input
                                  type="number"
                                  step="any"
                                  min="0"
                                  value={getDisplayValue(ex, 'weight_kg')}
                                  onChange={(e) => handleInlineEdit(ex.id, 'weight_kg', e.target.value)}
                                  onBlur={!readOnly ? () => handleInlineBlurSave(ex.id, 'weight_kg') : undefined}
                                  className="input w-20 text-sm text-right py-1 px-1.5"
                                  placeholder="-"
                                />
                              </div>
                            </td>
                          </>
                        )}

                        {!readOnly && (
                          <td className="py-1.5 px-2 text-right">
                            <button
                              onClick={() => handleDelete(ex.id)}
                              className="px-2 py-1 text-xs rounded text-white/30 hover:text-red-400 hover:bg-red-400/10 transition-colors"
                            >
                              &times;
                            </button>
                          </td>
                        )}
                      </tr>
                    ))}

                    {/* Circuit expanded: show exercises organized by round */}
                    {isExpanded && !isEditingGroup && isCirc && circuitInfo && (() => {
                      const { uniqueCount, rounds: roundCount } = circuitInfo;
                      return Array.from({ length: roundCount }, (_, roundIdx) => {
                        const roundExercises = group.exercises.slice(
                          roundIdx * uniqueCount,
                          (roundIdx + 1) * uniqueCount
                        );
                        return (
                          <Fragment key={`round-${roundIdx}`}>
                            <tr className="border-b border-secondary-muted/20 bg-secondary-muted/5">
                              <td className="py-1 px-1"></td>
                              <td colSpan={readOnly ? 3 : 4} className="py-1 px-2 pl-6">
                                <span className="text-xs font-medium text-white/40 uppercase">Round {roundIdx + 1}</span>
                              </td>
                            </tr>
                            {roundExercises.map((ex) => (
                              <tr
                                key={ex.id}
                                className="border-b border-secondary-muted/20 bg-secondary-muted/5"
                              >
                                <td className="py-1.5 px-1"></td>
                                <td className="py-1.5 px-2 pl-10 text-white/50 text-xs">{ex.exercise_name}</td>
                                <td className="py-1.5 px-2 text-right text-white/50">
                                  {ex.duration_seconds != null ? `${ex.duration_seconds}s` : '-'}
                                </td>
                                <td className="py-1.5 px-2 text-white/50 hidden sm:table-cell">
                                  {ex.rest_seconds != null ? `${ex.rest_seconds}s rest` : ''}
                                </td>
                              </tr>
                            ))}
                          </Fragment>
                        );
                      });
                    })()}

                    {/* Add Set button (not for circuits — use edit instead) */}
                    {isExpanded && !isEditingGroup && !isCirc && (
                      <tr className="border-b border-secondary-muted/20 bg-secondary-muted/5">
                        <td className="py-1 px-1"></td>
                        <td colSpan={isCond ? (readOnly ? 4 : 5) : (readOnly ? 3 : 4)} className="py-1 px-2 pl-6">
                          <button
                            onClick={() => handleAddSet(group)}
                            disabled={addingSetGroup === group.exerciseName}
                            className="text-xs text-accent hover:text-accent/80 active:scale-[0.97] transition-colors disabled:opacity-50"
                          >
                            {addingSetGroup === group.exerciseName ? 'Adding...' : '+ Add Set'}
                          </button>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Save edits button (shown when readOnly with pending changes) */}
      {readOnly && hasEdits && (
        <div className="mb-3">
          <button
            onClick={handleSaveEdits}
            disabled={savingEdits}
            className="px-4 py-2.5 min-h-[44px] rounded text-sm font-medium bg-accent text-[#090A3D] hover:bg-accent/80 active:scale-[0.97] transition-colors disabled:opacity-50"
          >
            {savingEdits ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      )}

      {/* Add Exercise Form */}
      {!readOnly && (
        showAddForm ? (
          <>
            {category === 'Conditioning' || category === 'Circuit' ? (
              <>
                {/* Category selector — shown only when session type doesn't lock category */}
                {trainingType !== 'Conditioning' && trainingType !== 'Circuit' && (
                  <div className="border-t border-secondary-muted/30 pt-3 mb-3">
                    <div className="flex items-center gap-2">
                      <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-accent/15 text-accent">
                        {category}
                      </span>
                      <button
                        type="button"
                        onClick={() => setShowCategoryDropdown(!showCategoryDropdown)}
                        className="text-xs text-white/40 hover:text-white/60 transition-colors"
                      >
                        Change
                      </button>
                    </div>
                    {showCategoryDropdown && (
                      <select
                        value={category}
                        onChange={(e) => {
                          setCategory(e.target.value);
                          setShowCategoryDropdown(false);
                        }}
                        className="select w-full sm:w-48 text-sm mt-2"
                      >
                        {EXERCISE_CATEGORIES.map((c) => (
                          <option key={c} value={c}>{c}</option>
                        ))}
                      </select>
                    )}
                  </div>
                )}
                {category === 'Circuit' ? (
                  <CircuitExerciseForm
                    sessionId={sessionId}
                    nextSetNumber={(exercises.length > 0 ? Math.max(...exercises.map(e => e.set_number)) : 0) + 1}
                    onSaved={() => {
                      setShowAddForm(false);
                      setShowCategoryDropdown(false);
                      loadExercises();
                    }}
                    onCancel={() => {
                      setShowAddForm(false);
                      setShowCategoryDropdown(false);
                    }}
                  />
                ) : (
                  <>
                    <div className="bg-accent/5 border border-accent/20 rounded-lg px-3 py-2 mb-3">
                      <p className="text-xs text-accent/80">Conditioning mode — configure intervals, durations and intensities</p>
                    </div>
                    <ConditioningExerciseForm
                      sessionId={sessionId}
                      nextSetNumber={(exercises.length > 0 ? Math.max(...exercises.map(e => e.set_number)) : 0) + 1}
                      onSaved={() => {
                        setShowAddForm(false);
                        setShowCategoryDropdown(false);
                        loadExercises();
                      }}
                      onCancel={() => {
                        setShowAddForm(false);
                        setShowCategoryDropdown(false);
                      }}
                    />
                  </>
                )}
              </>
            ) : (
              <form onSubmit={handleAddExercise} className="space-y-3">
                {/* Exercise Name — full width */}
                <div>
                  <label className="block text-xs text-white/60 mb-1">Exercise Name</label>
                  <ExerciseAutocomplete
                    value={exerciseName}
                    onChange={setExerciseName}
                    onSelect={handleLibrarySelect}
                  />
                </div>

                {/* Sets stepper + Category pill */}
                <div className="flex flex-wrap items-end gap-4">
                  <div>
                    <label className="block text-xs text-white/60 mb-2">Number of Sets</label>
                    <StepperInput
                      value={numberOfSets}
                      onChange={handleSetCount}
                      min={1}
                      max={20}
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-white/60 mb-1">Category</label>
                    <div className="flex items-center gap-2 min-h-[44px]">
                      <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-accent/15 text-accent">
                        {category}
                      </span>
                      <button
                        type="button"
                        onClick={() => setShowCategoryDropdown(!showCategoryDropdown)}
                        className="text-xs text-white/40 hover:text-white/60 transition-colors"
                      >
                        Change
                      </button>
                    </div>
                    {showCategoryDropdown && (
                      <select
                        value={category}
                        onChange={(e) => {
                          setCategory(e.target.value);
                          setShowCategoryDropdown(false);
                        }}
                        className="select w-full sm:w-48 text-sm mt-1"
                      >
                        {EXERCISE_CATEGORIES.map((c) => (
                          <option key={c} value={c}>{c}</option>
                        ))}
                      </select>
                    )}
                  </div>
                </div>

                {/* Per-set cards */}
                <div className="space-y-0">
                  {setConfigs.map((sc, i) => (
                    <div key={i}>
                      <div className="rounded bg-secondary-muted/5 px-3 py-2">
                        <div className="flex items-center gap-3">
                          <span className="text-xs text-white/50 w-10 shrink-0">Set {i + 1}</span>
                          <input
                            type="number"
                            min="1"
                            max="100"
                            value={sc.reps}
                            onChange={(e) =>
                              setSetConfigs(prev => prev.map((s, idx) => idx === i ? { ...s, reps: e.target.value } : s))
                            }
                            onFocus={selectOnFocus}
                            className="input w-20 text-sm text-center"
                            placeholder="reps"
                          />
                          <span className="text-xs text-white/40">reps @</span>
                          <input
                            type="number"
                            step="any"
                            min="0"
                            value={sc.weight_kg}
                            onChange={(e) =>
                              setSetConfigs(prev => prev.map((s, idx) => idx === i ? { ...s, weight_kg: e.target.value } : s))
                            }
                            onFocus={selectOnFocus}
                            className="input w-20 text-sm text-center"
                            placeholder="kg"
                          />
                          <span className="text-xs text-white/40">kg</span>
                        </div>
                      </div>

                      {/* Rest separator between sets */}
                      {i < setConfigs.length - 1 && (
                        <div className="flex items-center gap-3 py-2 px-4">
                          <div className="flex-1 border-t border-secondary-muted/20" />
                          <div className="flex items-center gap-2">
                            <label className="text-xs text-white/40 whitespace-nowrap">Rest</label>
                            <input
                              type="number"
                              min="0"
                              max="600"
                              value={restBetweenSetsArr[i] ?? ''}
                              onChange={(e) =>
                                setRestBetweenSetsArr(prev => {
                                  const next = [...prev];
                                  next[i] = e.target.value;
                                  return next;
                                })
                              }
                              onFocus={selectOnFocus}
                              className="input w-20 text-sm text-center"
                              placeholder="60"
                            />
                            <span className="text-xs text-white/40">sec</span>
                          </div>
                          <div className="flex-1 border-t border-secondary-muted/20" />
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setShowAddForm(false);
                      setShowCategoryDropdown(false);
                    }}
                    className="btn-secondary text-sm"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={saving}
                    className="btn-primary text-sm disabled:opacity-50"
                  >
                    {saving ? 'Adding...' : 'Add Exercise'}
                  </button>
                </div>
              </form>
            )}
          </>
        ) : (
          <div className="flex gap-2">
            <button
              onClick={() => {
                setShowAddForm(true);
              }}
              className="px-4 py-2.5 min-h-[44px] rounded text-sm font-medium bg-accent text-[#090A3D] hover:bg-accent/80 active:scale-[0.97] transition-colors"
            >
              + Add Exercise
            </button>
            <button
              onClick={() => setShowTemplatePicker(true)}
              className="px-4 py-2.5 min-h-[44px] rounded text-sm font-medium bg-accent/10 text-accent hover:bg-accent/20 active:scale-[0.97] transition-colors"
            >
              Import from Template
            </button>
          </div>
        )
      )}

      {!readOnly && showTemplatePicker && (
        <TemplatePickerModal
          sessionId={sessionId}
          existingExerciseCount={exercises.length}
          onClose={() => setShowTemplatePicker(false)}
          onApplied={() => {
            setShowTemplatePicker(false);
            loadExercises();
          }}
        />
      )}
    </div>
  );
}
