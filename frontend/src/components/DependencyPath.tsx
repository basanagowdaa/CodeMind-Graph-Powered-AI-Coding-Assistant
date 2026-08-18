import React from 'react';
import { ArrowRight, Info, HelpCircle } from 'lucide-react';
import { DependencyPathItem } from '../types';

interface DependencyPathProps {
  path: DependencyPathItem[];
}

export const DependencyPath: React.FC<DependencyPathProps> = ({ path }) => {
  if (!path || path.length === 0) return null;

  return (
    <div className="bg-darkBg border border-cardBorder rounded-lg p-4 font-mono text-xs text-slate-300 space-y-3">
      {/* Visual Chain */}
      <div className="flex flex-wrap items-center gap-2 leading-relaxed">
        {path.map((item, idx) => {
          const isLast = idx === path.length - 1;
          return (
            <React.Fragment key={idx}>
              <div className="flex flex-col items-center bg-slate-900 border border-cardBorder rounded px-2.5 py-1.5 min-w-[80px] text-center">
                <span className="text-white font-semibold">{item.source}</span>
              </div>
              <div className="flex flex-col items-center justify-center text-slate-500 shrink-0 px-1">
                <ArrowRight size={14} className="text-accentPurple" />
                <span className="text-[9px] font-bold text-accentPurple uppercase tracking-wider scale-90">
                  {item.predicate}
                </span>
              </div>
              {isLast && (
                <div className="flex flex-col items-center bg-slate-900 border border-accentPurple rounded px-2.5 py-1.5 min-w-[80px] text-center shadow-lg shadow-violet-900/10">
                  <span className="text-white font-semibold">{item.target}</span>
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Triplet explanations / contexts */}
      <div className="border-t border-cardBorder pt-2 mt-2 space-y-1.5 text-[11px] text-slate-400 font-sans">
        {path.map((item, idx) => {
          if (!item.context) return null;
          return (
            <div key={idx} className="flex items-start gap-1.5">
              <span className="text-accentPurple shrink-0 select-none">↳</span>
              <span>{item.context}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
