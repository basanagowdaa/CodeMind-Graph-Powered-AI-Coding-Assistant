import React, { useEffect, useState } from 'react';
import { Cpu, Database, RefreshCw, BarChart2, ShieldCheck, Zap, AlertCircle } from 'lucide-react';
import { api } from '../services/api';
import { BenchmarkResponse, QueryBenchmark } from '../types';

interface BenchmarkProps {
  repositoryId: string;
}

export const Benchmark: React.FC<BenchmarkProps> = ({ repositoryId }) => {
  const [data, setData] = useState<BenchmarkResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runBenchmark = async () => {
    if (!repositoryId) return;
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const resp = await api.runBenchmark(repositoryId);
      setData(resp);
    } catch (err: any) {
      setError(err.message || 'Failed to run benchmarks.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runBenchmark();
  }, [repositoryId]);

  if (!repositoryId) {
    return (
      <div className="bg-cardBg border border-cardBorder rounded-lg p-8 text-center text-slate-500 font-mono">
        Please select or ingest a repository on the Overview dashboard first.
      </div>
    );
  }

  return (
    <div className="space-y-6 text-sm">
      {/* Benchmark Header */}
      <div className="bg-cardBg border border-cardBorder rounded-lg p-5 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-base font-bold font-mono text-white mb-2 flex items-center gap-2">
            <BarChart2 size={18} className="text-accentPurple" /> Retrieval Benchmarks
          </h2>
          <p className="text-slate-400 text-xs">
            Evaluates vector-only similarity search (Baseline) vs HydraDB-enabled context graphs (CodeMind).
          </p>
        </div>
        <button
          onClick={runBenchmark}
          disabled={loading}
          className="flex items-center gap-2 bg-accentPurple hover:bg-violet-600 active:bg-violet-700 disabled:opacity-50 text-white font-mono font-semibold py-2 px-4 rounded transition duration-150"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          {loading ? 'Executing...' : 'Run Benchmark'}
        </button>
      </div>

      {loading && (
        <div className="bg-cardBg border border-cardBorder rounded-lg p-8 text-center text-slate-500 font-mono text-xs gap-2 flex items-center justify-center">
          <RefreshCw className="animate-spin text-accentPurple" size={16} /> Running benchmark evaluations across typical queries...
        </div>
      )}

      {error && (
        <div className="bg-rose-950/20 border border-rose-800 text-rose-300 rounded p-4 font-mono text-xs">
          {error}
        </div>
      )}

      {data && (
        <>
          {/* Comparison Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 font-mono">
            {/* Average Latency */}
            <div className="bg-cardBg border border-cardBorder rounded-lg p-5">
              <span className="text-[10px] text-slate-400 uppercase font-bold tracking-wider block mb-2">
                Avg Latency Comparison
              </span>
              <div className="space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-500">Baseline (Vector):</span>
                  <span className="text-white font-bold">{data.averages.baseline_latency_ms} ms</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-accentPurple font-semibold">CodeMind (Graph):</span>
                  <span className="text-white font-bold">{data.averages.codemind_latency_ms} ms</span>
                </div>
                <div className="border-t border-cardBorder pt-2 mt-2 flex justify-between items-center text-[10px] text-slate-400">
                  <span>Latency difference:</span>
                  <span className="text-amber-400 font-bold">+{data.averages.latency_increase_pct}%</span>
                </div>
              </div>
            </div>

            {/* Relationships Found */}
            <div className="bg-cardBg border border-cardBorder rounded-lg p-5">
              <span className="text-[10px] text-slate-400 uppercase font-bold tracking-wider block mb-2">
                Relations Retrieved
              </span>
              <div className="space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-500">Baseline (Vector):</span>
                  <span className="text-white font-bold">0 connections</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-accentPurple font-semibold">CodeMind (Graph):</span>
                  <span className="text-white font-bold">{data.metrics.total_relations_retrieved} connections</span>
                </div>
                <div className="border-t border-cardBorder pt-2 mt-2 flex justify-between items-center text-[10px] text-slate-400">
                  <span>Grounded paths:</span>
                  <span className="text-emerald-400 font-bold">{data.metrics.grounded_paths_available} paths</span>
                </div>
              </div>
            </div>

            {/* Explanation Benefit */}
            <div className="bg-cardBg border border-cardBorder rounded-lg p-5 flex flex-col justify-between">
              <div>
                <span className="text-[10px] text-slate-400 uppercase font-bold tracking-wider block mb-2">
                  Benefit summary
                </span>
                <p className="text-slate-300 text-[11px] font-sans leading-relaxed">
                  {data.metrics.graph_retrieval_benefit}
                </p>
              </div>
            </div>
          </div>

          {/* Query Breakdown Table */}
          <div className="bg-cardBg border border-cardBorder rounded-lg p-5 overflow-hidden">
            <h3 className="text-sm font-bold font-mono text-white mb-3 flex items-center gap-1.5">
              <Zap size={16} className="text-accentPurple" /> Evaluation Queries Breakdown
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left font-mono text-xs border-collapse">
                <thead>
                  <tr className="border-b border-cardBorder text-slate-400">
                    <th className="py-2.5 pr-4 font-semibold">Evaluation Query</th>
                    <th className="py-2.5 px-4 font-semibold text-center">Baseline Latency</th>
                    <th className="py-2.5 px-4 font-semibold text-center">CodeMind Latency</th>
                    <th className="py-2.5 px-4 font-semibold text-center">Relations Found</th>
                    <th className="py-2.5 pl-4 font-semibold text-right">Accuracy / Completeness</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-cardBorder">
                  {data.queries.map((q, idx) => (
                    <tr key={idx} className="hover:bg-slate-900/40">
                      <td className="py-3 pr-4 text-white font-semibold max-w-xs md:max-w-md truncate">
                        {q.question}
                      </td>
                      <td className="py-3 px-4 text-center text-slate-400">
                        {q.baseline.latency_ms} ms
                      </td>
                      <td className="py-3 px-4 text-center text-slate-300 font-bold">
                        {q.codemind.latency_ms} ms
                      </td>
                      <td className="py-3 px-4 text-center text-accentPurple font-bold">
                        {q.codemind.relations_found}
                      </td>
                      <td className="py-3 pl-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-16 bg-slate-950 rounded-full h-1.5 overflow-hidden border border-cardBorder">
                            <div
                              className="bg-accentPurple h-full rounded-full"
                              style={{ width: `${q.codemind.completeness_score * 100}%` }}
                            ></div>
                          </div>
                          <span className="text-[10px] text-slate-400">
                            {Math.round(q.codemind.completeness_score * 100)}%
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
