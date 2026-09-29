'use client';

import type { ProgramPackage } from '@/lib/types';

interface ProgramCardProps {
  program: ProgramPackage;
  onViewDetail: () => void;
  onInstall: () => void;
  onUninstall: () => void;
}

export function ProgramCard({ program, onViewDetail, onInstall, onUninstall }: ProgramCardProps) {
  return (
    <div className="border border-secondary-muted rounded-lg p-4 hover:border-accent/30 transition-colors flex flex-col">
      <div className="flex-1">
        <div className="flex items-start justify-between mb-2">
          <h3 className="font-medium text-sm leading-tight">{program.program_name}</h3>
          <span className="text-[10px] font-medium uppercase px-2 py-0.5 rounded-full bg-white/5 text-white/40 shrink-0 ml-2">
            {program.category}
          </span>
        </div>
        {program.description && (
          <p className="text-xs text-white/50 mb-3 line-clamp-2">{program.description}</p>
        )}
        <p className="text-xs text-white/30">
          {program.template_count} template{program.template_count !== 1 ? 's' : ''}
        </p>
      </div>
      <div className="flex items-center gap-2 mt-3 pt-3 border-t border-secondary-muted/30">
        <button
          onClick={onViewDetail}
          className="flex-1 py-2 min-h-[44px] rounded text-xs font-medium bg-white/5 text-white/60 hover:bg-white/10 hover:text-white transition-colors"
        >
          View Details
        </button>
        {program.is_installed ? (
          <button
            onClick={(e) => { e.stopPropagation(); onUninstall(); }}
            className="flex-1 py-2 min-h-[44px] rounded text-xs font-medium bg-accent/10 text-accent hover:bg-accent/20 transition-colors"
          >
            Installed
          </button>
        ) : (
          <button
            onClick={(e) => { e.stopPropagation(); onInstall(); }}
            className="flex-1 py-2 min-h-[44px] rounded text-xs font-medium bg-accent text-[#090A3D] hover:bg-accent/80 transition-colors"
          >
            Install
          </button>
        )}
      </div>
    </div>
  );
}
