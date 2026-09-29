'use client';

import { forwardRef } from 'react';
import type { ProgrammeForm } from '@/lib/types';

const SECTION_LABELS: Record<string, string> = {
  hand_prep: 'HAND PREP',
  extended_warmup: 'EXTENDED WARM-UP',
  superset_1: 'SUPERSET 1',
  superset_2: 'SUPERSET 2',
  superset_3: 'SUPERSET 3',
  core_circuit: 'CORE CIRCUIT',
  perform_separate: 'PERFORM SEPARATE',
};

const SUPERSET_KEYS = new Set(['superset_1', 'superset_2', 'superset_3']);

interface ProgrammeFormPrintViewProps {
  form: ProgrammeForm;
}

export const ProgrammeFormPrintView = forwardRef<HTMLDivElement, ProgrammeFormPrintViewProps>(
  function ProgrammeFormPrintView({ form }, ref) {
    return (
      <div ref={ref} className="report-print-layout">
        {/* Title page section */}
        <div className="report-section">
          <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 4 }}>{form.form_name}</h1>
          {form.description && (
            <p style={{ fontSize: 14, color: '#555', marginBottom: 8 }}>{form.description}</p>
          )}
          <p style={{ fontSize: 12, color: '#888' }}>
            {form.num_weeks} weeks &middot; {form.sessions_per_week} sessions/week
          </p>
        </div>

        {form.form_data.sessions.map((session) => (
          <div key={session.session_number} className="report-section">
            <div className="report-section-title">
              {session.session_name || `Session ${session.session_number}`}
            </div>

            {session.sections.map((section) => {
              const label = SECTION_LABELS[section.section_type] ?? section.section_type;
              const isSuperset = SUPERSET_KEYS.has(section.section_type);

              if (section.exercises.length === 0) return null;

              if (isSuperset) {
                const slotA = section.exercises.find((ex) => ex.slot === 'A');
                const slotB = section.exercises.find((ex) => ex.slot === 'B');

                return (
                  <div key={section.section_type} style={{ marginBottom: 16 }}>
                    <h3 style={{ fontSize: 13, fontWeight: 600, color: '#090A3D', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                      {label}
                    </h3>

                    {slotA && (
                      <div style={{ marginBottom: 8 }}>
                        <p style={{ fontSize: 12, fontWeight: 600, marginBottom: 2 }}>
                          A: {slotA.exercise_name}
                          {slotA.notes && <span style={{ fontWeight: 400, color: '#666', marginLeft: 8 }}>{slotA.notes}</span>}
                        </p>
                        {slotA.weeks && slotA.weeks.length > 0 && (
                          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11, marginTop: 4 }}>
                            <thead>
                              <tr style={{ borderBottom: '1px solid #ddd' }}>
                                <th style={{ textAlign: 'left', padding: '4px 6px', fontWeight: 600 }}>Week</th>
                                <th style={{ textAlign: 'left', padding: '4px 6px', fontWeight: 600 }}>Reps</th>
                                <th style={{ textAlign: 'left', padding: '4px 6px', fontWeight: 600 }}>Sets</th>
                                <th style={{ textAlign: 'left', padding: '4px 6px', fontWeight: 600 }}>Rec. Load</th>
                                <th style={{ textAlign: 'left', padding: '4px 6px', fontWeight: 600, minWidth: 80 }}>Actual</th>
                              </tr>
                            </thead>
                            <tbody>
                              {slotA.weeks.map((w, i) => (
                                <tr key={i} style={{ borderBottom: '1px solid #eee' }}>
                                  <td style={{ padding: '4px 6px' }}>{w.week_number}</td>
                                  <td style={{ padding: '4px 6px' }}>{w.reps_text || '-'}</td>
                                  <td style={{ padding: '4px 6px' }}>{w.sets}</td>
                                  <td style={{ padding: '4px 6px' }}>
                                    {w.recommended_weight_kg != null ? `${w.recommended_weight_kg} kg` : '-'}
                                  </td>
                                  <td style={{ padding: '4px 6px', borderBottom: '1px dotted #ccc' }}></td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        )}
                      </div>
                    )}

                    {slotB && (
                      <div>
                        <p style={{ fontSize: 12, fontWeight: 600, marginBottom: 2 }}>
                          B: {slotB.exercise_name}
                          {slotB.description && <span style={{ fontWeight: 400, color: '#666', marginLeft: 8 }}>{slotB.description}</span>}
                        </p>
                      </div>
                    )}
                  </div>
                );
              }

              // Simple section (hand_prep, extended_warmup, core_circuit, perform_separate)
              return (
                <div key={section.section_type} style={{ marginBottom: 16 }}>
                  <h3 style={{ fontSize: 13, fontWeight: 600, color: '#090A3D', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                    {label}
                    {section.section_type === 'core_circuit' && section.circuit_sets && (
                      <span style={{ fontWeight: 400, fontSize: 11, color: '#666', marginLeft: 8 }}>
                        Circuit Sets: {section.circuit_sets}
                      </span>
                    )}
                  </h3>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid #ddd' }}>
                        <th style={{ textAlign: 'left', padding: '4px 6px', fontWeight: 600 }}>Exercise</th>
                        <th style={{ textAlign: 'left', padding: '4px 6px', fontWeight: 600 }}>Description</th>
                      </tr>
                    </thead>
                    <tbody>
                      {section.exercises.map((ex, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid #eee' }}>
                          <td style={{ padding: '4px 6px' }}>{ex.exercise_name || '-'}</td>
                          <td style={{ padding: '4px 6px', color: '#555' }}>{ex.description || '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              );
            })}
          </div>
        ))}

        {/* Footer */}
        <div style={{ marginTop: 24, paddingTop: 12, borderTop: '1px solid #ddd', fontSize: 10, color: '#999', textAlign: 'center' }}>
          {form.form_name} &middot; Generated {new Date().toLocaleDateString('en-GB')}
        </div>
      </div>
    );
  }
);
