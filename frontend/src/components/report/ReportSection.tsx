'use client';

interface ReportSectionProps {
  title: string;
  notes?: string;
  children: React.ReactNode;
}

export function ReportSection({ title, notes, children }: ReportSectionProps) {
  return (
    <div className="report-section">
      <h2 className="report-section-title">{title}</h2>
      {children}
      {notes && (
        <div className="report-notes">
          <strong>Coach Notes:</strong> {notes}
        </div>
      )}
    </div>
  );
}
