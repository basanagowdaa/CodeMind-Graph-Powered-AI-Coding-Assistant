import React, { useEffect, useState } from 'react';
import { Play, Database, FileCode, Cpu, Layers, GitFork, ArrowRight, RefreshCw, Plus, ShieldAlert } from 'lucide-react';
import { api } from '../services/api';
import { Repository } from '../types';

interface OverviewProps {
  onSelectRepository: (repoId: string) => void;
  selectedRepositoryId: string;
}

export const Overview: React.FC<OverviewProps> = ({
  onSelectRepository,
  selectedRepositoryId,
}) => {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [source, setSource] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingList, setLoadingList] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Job status polling
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<Repository | null>(null);

  const fetchRepositories = async () => {
    setLoadingList(true);
    try {
      const list = await api.listRepositories();
      setRepos(list);
      // Auto-select first repository if none selected
      if (list.length > 0 && !selectedRepositoryId) {
        onSelectRepository(list[0].repository_id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch repositories');
    } finally {
      setLoadingList(false);
    }
  };

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!source.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const job = await api.analyzeRepository(source);
      setActiveJobId(job.repository_id);
      setJobStatus(job);
      setSource('');
      await fetchRepositories();
    } catch (err: any) {
      setError(err.message || 'Failed to trigger repository analysis.');
    } finally {
      setLoading(false);
    }
  };

  // Poll active analysis jobs
  useEffect(() => {
    if (!activeJobId) return;

    let timer: any;

    const poll = async () => {
      try {
        const job = await api.getRepositoryStatus(activeJobId);
        setJobStatus(job);
        if (job.status === 'ready' || job.status === 'error') {
          setActiveJobId(null);
          await fetchRepositories();
          if (job.status === 'ready') {
            onSelectRepository(job.repository_id);
          }
        } else {
          timer = setTimeout(poll, 3000);
        }
      } catch (err: any) {
        setError(err.message || 'Error tracking analysis job.');
        setActiveJobId(null);
      }
    };

    poll();
    return () => clearTimeout(timer);
  }, [activeJobId]);

  useEffect(() => {
    fetchRepositories();
  }, []);

  const activeRepo = repos.find((r) => r.repository_id === selectedRepositoryId);

  return (
    <div className="space-y-6 text-sm">
      {/* Upper Grid: Load Repo / Active Repo statistics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Panel 1: Analyze New Repo */}
        <div className="lg:col-span-1 bg-cardBg border border-cardBorder rounded-lg p-5 flex flex-col justify-between">
          <div>
            <h2 className="text-base font-bold font-mono text-white mb-2 flex items-center gap-2">
              <Plus size={18} className="text-accentPurple" /> Ingest Repository
            </h2>
            <p className="text-slate-400 text-xs mb-4 leading-relaxed">
              Enter a local folder path or public HTTPS GitHub repository URL. CodeMind will statically parse it and index it in HydraDB using the BYOG context graph method.
            </p>
          </div>

          <form onSubmit={handleAnalyze} className="space-y-3">
            <div>
              <input
                type="text"
                value={source}
                onChange={(e) => setSource(e.target.value)}
                placeholder="e.g. C:\HACK PROJECTS\Codemind\demo-repository"
                disabled={loading || !!activeJobId}
                className="w-full bg-darkBg border border-cardBorder rounded px-3 py-2 text-slate-200 font-mono text-xs focus:outline-none focus:border-accentPurple placeholder:opacity-50 disabled:opacity-50"
              />
            </div>
            <button
              type="submit"
              disabled={loading || !source.trim() || !!activeJobId}
              className="w-full flex items-center justify-center gap-2 bg-accentPurple hover:bg-violet-600 active:bg-violet-700 disabled:opacity-50 text-white font-mono font-semibold py-2 px-4 rounded transition duration-150"
            >
              {loading ? 'Queuing...' : 'Analyze Repo'} <ArrowRight size={14} />
            </button>
          </form>
        </div>

        {/* Panel 2: Current Job Status / Progress */}
        <div className="lg:col-span-2 bg-cardBg border border-cardBorder rounded-lg p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-base font-bold font-mono text-white flex items-center gap-2">
                <RefreshCw size={18} className="text-accentBlue" /> Ingestion Queue
              </h2>
              {loadingList && <span className="text-xs text-slate-500 font-mono">Syncing...</span>}
            </div>

            {/* If there is a job running */}
            {jobStatus && (jobStatus.status !== 'ready' && jobStatus.status !== 'error') ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-accentBlue font-bold uppercase">
                    Job: {jobStatus.status}
                  </span>
                  <span className="font-mono text-xs text-slate-400">{jobStatus.progress}%</span>
                </div>
                {/* Progress bar */}
                <div className="w-full bg-darkBg rounded-full h-2 overflow-hidden border border-cardBorder">
                  <div
                    className="bg-accentPurple h-full rounded-full transition-all duration-500"
                    style={{ width: `${jobStatus.progress}%` }}
                  ></div>
                </div>
                <p className="text-slate-300 font-mono text-xs italic">{jobStatus.message}</p>
              </div>
            ) : jobStatus?.status === 'error' ? (
              <div className="bg-rose-950/30 border border-rose-800 rounded p-4 flex items-start gap-3">
                <ShieldAlert className="text-rose-400 shrink-0 mt-0.5" size={18} />
                <div>
                  <h4 className="text-xs font-bold text-rose-300 font-mono uppercase mb-1">Analysis Failed</h4>
                  <p className="text-[11px] text-rose-200/80 font-mono leading-relaxed">{jobStatus.error}</p>
                </div>
              </div>
            ) : activeRepo ? (
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 bg-accentPurple/20 border border-accentPurple/40 rounded text-[10px] font-mono text-accentPurple uppercase font-bold">
                    ACTIVE
                  </span>
                  <h3 className="text-base font-bold font-mono text-white break-all">
                    {activeRepo.repository_name}
                  </h3>
                </div>
                <p className="text-xs text-slate-400 font-mono break-all">{activeRepo.repository_url}</p>
                <div className="bg-darkBg border border-cardBorder rounded p-3 text-xs font-mono text-emerald-400">
                  Ready for queries in HydraDB database: {activeRepo.repository_id}
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-500 font-mono text-xs">
                No active ingestion job. Load a repository to start.
              </div>
            )}
          </div>

          {/* Error Banner */}
          {error && (
            <div className="mt-4 bg-rose-950/20 border border-rose-800 text-rose-300 rounded p-3 font-mono text-xs flex items-center gap-2">
              <ShieldAlert size={16} /> <span>{error}</span>
            </div>
          )}
        </div>
      </div>

      {/* Repo Statistics Grid */}
      {activeRepo?.statistics && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="bg-cardBg border border-cardBorder rounded-lg p-4 text-center">
            <span className="text-[10px] text-slate-400 font-mono uppercase font-bold tracking-wider block mb-1">
              Files
            </span>
            <span className="text-2xl font-bold font-mono text-white">{activeRepo.statistics.files}</span>
          </div>
          <div className="bg-cardBg border border-cardBorder rounded-lg p-4 text-center">
            <span className="text-[10px] text-slate-400 font-mono uppercase font-bold tracking-wider block mb-1">
              Functions
            </span>
            <span className="text-2xl font-bold font-mono text-accentPurple">{activeRepo.statistics.functions}</span>
          </div>
          <div className="bg-cardBg border border-cardBorder rounded-lg p-4 text-center">
            <span className="text-[10px] text-slate-400 font-mono uppercase font-bold tracking-wider block mb-1">
              Classes
            </span>
            <span className="text-2xl font-bold font-mono text-accentBlue">{activeRepo.statistics.classes}</span>
          </div>
          <div className="bg-cardBg border border-cardBorder rounded-lg p-4 text-center">
            <span className="text-[10px] text-slate-400 font-mono uppercase font-bold tracking-wider block mb-1">
              APIs
            </span>
            <span className="text-2xl font-bold font-mono text-accentGreen">{activeRepo.statistics.apis}</span>
          </div>
          <div className="bg-cardBg border border-cardBorder rounded-lg p-4 text-center">
            <span className="text-[10px] text-slate-400 font-mono uppercase font-bold tracking-wider block mb-1">
              Tests
            </span>
            <span className="text-2xl font-bold font-mono text-accentPink">{activeRepo.statistics.tests}</span>
          </div>
          <div className="bg-cardBg border border-cardBorder rounded-lg p-4 text-center">
            <span className="text-[10px] text-slate-400 font-mono uppercase font-bold tracking-wider block mb-1">
              Relationships
            </span>
            <span className="text-2xl font-bold font-mono text-white">{activeRepo.statistics.relationships}</span>
          </div>
        </div>
      )}

      {/* Select Repo List */}
      {repos.length > 0 && (
        <div className="bg-cardBg border border-cardBorder rounded-lg p-5">
          <h3 className="text-sm font-bold font-mono text-white mb-3">
            Select Repository ({repos.length} Ingested)
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {repos.map((r) => {
              const isSelected = r.repository_id === selectedRepositoryId;
              return (
                <div
                  key={r.repository_id}
                  onClick={() => onSelectRepository(r.repository_id)}
                  className={`border rounded-lg p-4 cursor-pointer transition flex items-center justify-between ${
                    isSelected
                      ? 'bg-accentPurple/10 border-accentPurple shadow-lg shadow-violet-950/20'
                      : 'bg-darkBg border-cardBorder hover:border-slate-700'
                  }`}
                >
                  <div>
                    <h4 className="font-bold font-mono text-slate-200 truncate max-w-[200px]">
                      {r.repository_name}
                    </h4>
                    <span className="text-[10px] font-mono text-slate-500 block truncate max-w-[200px]">
                      {r.repository_id}
                    </span>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase ${
                    r.status === 'ready'
                      ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                      : 'bg-slate-900 text-slate-500 border border-slate-800'
                  }`}>
                    {r.status}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
