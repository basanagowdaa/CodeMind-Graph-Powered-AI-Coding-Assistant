import React, { useEffect, useState } from 'react';
import { Play, Network, CheckCircle2, Database, Cpu } from 'lucide-react';
import { api } from '../services/api';
import { GraphNode, ImpactAnalysisResponse } from '../types';
import { DependencyPath } from '../components/DependencyPath';

interface ImpactAnalysisProps {
  repositoryId: string;
  selectedEntity: GraphNode | null;
  onClearEntity: () => void;
}

const BLAST_RADIUS_COLORS = {
  none: 'bg-emerald-950/40 border-emerald-800 text-emerald-300',
  low: 'bg-emerald-950/40 border-emerald-800 text-emerald-400',
  medium: 'bg-amber-950/40 border-amber-800 text-amber-400',
  high: 'bg-orange-950/40 border-orange-800 text-orange-400',
  critical: 'bg-rose-950/40 border-rose-800 text-rose-400 animate-pulse',
};

export const ImpactAnalysis: React.FC<ImpactAnalysisProps> = ({
  repositoryId,
  selectedEntity,
  onClearEntity,
}) => {
  const [data, setData] = useState<ImpactAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchImpact = async () => {
    if (!repositoryId || !selectedEntity) return;
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const resp = await api.analyzeImpact(
        repositoryId,
        selectedEntity.id,
        selectedEntity.name,
        selectedEntity.type
      );
      setData(resp);
    } catch (err: any) {
      setError(err.message || 'Failed to execute impact analysis.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchImpact();
  }, [repositoryId, selectedEntity]);

  if (!repositoryId) {
    return (
      <div className="bg-cardBg border border-cardBorder rounded-lg p-8 text-center text-slate-500 font-mono">
        Please select or ingest a repository on the Overview dashboard first.
      </div>
    );
  }

  if (!selectedEntity) {
    return (
      <div className="bg-cardBg border border-cardBorder rounded-lg p-8 text-center max-w-xl mx-auto space-y-4">
        <Play className="mx-auto text-accentPurple animate-pulse" size={36} />
        <h3 className="text-base font-bold font-mono text-white">BEFORE YOU CHANGE IT</h3>
        <p className="text-slate-400 text-xs leading-relaxed font-sans">
          Select a function, class, file, or API on the Code Map page, and click the &quot;BEFORE YOU CHANGE IT&quot; button to analyze the ripple effect of changing it.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 text-sm">
      {/* Entity Profile & Blast Radius Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 bg-cardBg border border-cardBorder rounded-lg p-5">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[10px] bg-slate-800 border border-slate-700 px-2 py-0.5 rounded font-mono uppercase font-bold text-slate-400">
              Target Entity
            </span>
            <span className="text-slate-400 font-mono text-xs truncate">{selectedEntity.file}</span>
          </div>
          <h2 className="text-lg font-bold font-mono text-white break-all mb-3">
            {selectedEntity.name}()
          </h2>
          <button
            onClick={onClearEntity}
            className="text-slate-400 hover:text-white font-mono text-xs"
          >
            ← Clear / Select another entity
          </button>
        </div>

        {/* Blast Radius Widget */}
        <div className="lg:col-span-1 bg-cardBg border border-cardBorder rounded-lg p-5 flex flex-col items-center justify-center text-center">
          <span className="text-[10px] text-slate-400 font-mono uppercase font-bold tracking-wider mb-1">
            Blast Radius
          </span>
          {data ? (
            <div className="space-y-1">
              <span className={`px-4 py-1.5 rounded-full border text-sm font-mono font-bold uppercase ${BLAST_RADIUS_COLORS[data.blast_radius]}`}>
                {data.blast_radius}
              </span>
              <span className="text-[10px] font-mono text-slate-500 block pt-1.5">
                {data.total_impacted} affected components
              </span>
            </div>
          ) : (
            <span className="text-slate-500 font-mono text-xs">Calculating...</span>
          )}
        </div>
      </div>

      {loading && (
        <div className="bg-cardBg border border-cardBorder rounded-lg p-8 text-center text-slate-500 font-mono text-xs gap-2 flex items-center justify-center">
          <Cpu className="animate-spin text-accentPurple" size={16} /> Evaluating code dependencies in HydraDB...
        </div>
      )}

      {error && (
        <div className="bg-rose-950/20 border border-rose-800 text-rose-300 rounded p-4 font-mono text-xs">
          {error}
        </div>
      )}

      {data && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Column 1 & 2: Categorized Affected Components list */}
          <div className="lg:col-span-2 space-y-6">
            {/* Callers */}
            {data.callers.length > 0 && (
              <div className="bg-cardBg border border-cardBorder rounded-lg p-5">
                <h3 className="text-sm font-bold font-mono text-white mb-3 flex items-center gap-2">
                  <Play size={16} className="text-accentPurple" /> Downstream Callers ({data.callers.length})
                </h3>
                <div className="space-y-2">
                  {data.callers.map((c) => (
                    <div key={c.id} className="bg-darkBg border border-cardBorder rounded p-3 flex justify-between items-center font-mono text-xs">
                      <div>
                        <span className="text-white font-semibold">{c.name}()</span>
                        <span className="text-[10px] text-slate-500 block truncate max-w-sm md:max-w-md">
                          {c.file}:{c.line}
                        </span>
                      </div>
                      <span className="px-2 py-0.5 bg-slate-900 border border-cardBorder text-slate-400 rounded text-[9px]">
                        {c.impact_level}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Test Functions */}
            {data.tests.length > 0 && (
              <div className="bg-cardBg border border-cardBorder rounded-lg p-5">
                <h3 className="text-sm font-bold font-mono text-white mb-3 flex items-center gap-2">
                  <CheckCircle2 size={16} className="text-accentPink" /> Test Cases Affected ({data.tests.length})
                </h3>
                <div className="space-y-2">
                  {data.tests.map((t) => (
                    <div key={t.id} className="bg-darkBg border border-cardBorder rounded p-3 flex justify-between items-center font-mono text-xs">
                      <div>
                        <span className="text-white font-semibold">{t.name}</span>
                        <span className="text-[10px] text-slate-500 block truncate max-w-sm">
                          {t.file}
                        </span>
                      </div>
                      <span className="px-2 py-0.5 bg-accentPink/10 border border-accentPink/30 text-accentPink rounded text-[9px] font-bold">
                        RUN REQUIRED
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* APIs exposed */}
            {data.apis.length > 0 && (
              <div className="bg-cardBg border border-cardBorder rounded-lg p-5">
                <h3 className="text-sm font-bold font-mono text-white mb-3 flex items-center gap-2">
                  <Network size={16} className="text-accentGreen" /> Exposed API Endpoints ({data.apis.length})
                </h3>
                <div className="space-y-2">
                  {data.apis.map((a) => (
                    <div key={a.id} className="bg-darkBg border border-cardBorder rounded p-3 flex justify-between items-center font-mono text-xs">
                      <div>
                        <span className="text-white font-bold text-accentGreen">{a.name}</span>
                        <span className="text-[10px] text-slate-500 block">
                          {a.file}
                        </span>
                      </div>
                      <span className="px-2 py-0.5 bg-emerald-950 text-emerald-400 border border-emerald-800 rounded text-[9px] font-bold uppercase">
                        Direct API
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* If no structural impacts found */}
            {data.total_impacted === 0 && (
              <div className="bg-cardBg border border-cardBorder rounded-lg p-6 text-center text-slate-500 font-mono">
                No direct structural callers or test files found in the repository index.
              </div>
            )}
          </div>

          {/* Column 3: Graph Dependency Paths (HydraDB query_paths) */}
          <div className="lg:col-span-1 space-y-6">
            <div className="bg-cardBg border border-cardBorder rounded-lg p-5">
              <h3 className="text-sm font-bold font-mono text-white mb-1 flex items-center gap-2">
                <Database size={16} className="text-accentPurple" /> Graph Context Paths
              </h3>
              <p className="text-[10px] text-slate-500 font-mono mb-4">
                Paths retrieved from HydraDB matching: &quot;What could break if {selectedEntity.name} changes?&quot;
              </p>
              
              {data.dependency_paths && data.dependency_paths.length > 0 ? (
                <div className="space-y-4">
                  {data.dependency_paths.map((path, idx) => (
                    <DependencyPath key={idx} path={path} />
                  ))}
                </div>
              ) : (
                <div className="bg-darkBg border border-cardBorder rounded p-4 text-center text-slate-500 font-mono text-xs">
                  No dependency paths returned for this query in the HydraDB graph index.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
