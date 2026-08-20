import React, { useEffect, useState } from 'react';
import { Database, ShieldCheck, ShieldAlert, Cpu, Settings as SettingsIcon, Layers, Server } from 'lucide-react';
import { api } from '../services/api';
import { ConnectionStatus } from '../types';

export const Settings: React.FC = () => {
  const [status, setStatus] = useState<ConnectionStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getHealth();
      setStatus(data);
    } catch (err: any) {
      setError(err.message || 'Failed to check server health');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <div className="space-y-6 text-sm">
      {/* Settings Header */}
      <div className="bg-cardBg border border-cardBorder rounded-lg p-5">
        <h2 className="text-base font-bold font-mono text-white mb-2 flex items-center gap-2">
          <SettingsIcon size={18} className="text-accentPurple" /> Environment Settings
        </h2>
        <p className="text-slate-400 text-xs">
          View configuration states, API connectivity, and active database namespaces. CodeMind integrates HydraDB as its core context engine.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* HydraDB connection stats */}
        <div className="bg-cardBg border border-cardBorder rounded-lg p-5 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold font-mono text-white mb-4 flex items-center gap-2">
              <Database size={16} className="text-accentPurple" /> HydraDB Connection Status
            </h3>

            {status ? (
              <div className="space-y-4">
                <div className={`p-4 rounded border font-mono text-xs flex items-start gap-3 ${
                  status.connected
                    ? 'bg-emerald-950/20 border-emerald-800 text-emerald-300'
                    : 'bg-rose-950/20 border-rose-800 text-rose-300'
                }`}>
                  {status.connected ? (
                    <ShieldCheck className="text-emerald-400 shrink-0" size={18} />
                  ) : (
                    <ShieldAlert className="text-rose-400 shrink-0" size={18} />
                  )}
                  <div>
                    <h4 className="font-bold uppercase mb-1">
                      {status.connected ? 'Connection Established' : 'Connection Failed'}
                    </h4>
                    <p className="opacity-90">{status.message}</p>
                  </div>
                </div>

                {status.connected && (
                  <div className="grid grid-cols-2 gap-4 pt-2">
                    <div className="bg-darkBg border border-cardBorder rounded p-3 text-center">
                      <span className="text-[10px] text-slate-400 font-mono uppercase font-bold tracking-wider block mb-1">
                        Active Databases
                      </span>
                      <span className="text-xl font-bold font-mono text-white">
                        {status.databases_count}
                      </span>
                    </div>
                    <div className="bg-darkBg border border-cardBorder rounded p-3 text-center">
                      <span className="text-[10px] text-slate-400 font-mono uppercase font-bold tracking-wider block mb-1">
                        SDK Version
                      </span>
                      <span className="text-xl font-bold font-mono text-accentPurple">
                        v2.1.2
                      </span>
                    </div>
                  </div>
                )}
              </div>
            ) : loading ? (
              <div className="text-slate-500 font-mono text-xs flex items-center gap-2">
                <Server size={14} className="animate-spin text-accentPurple" /> Ping in progress...
              </div>
            ) : error ? (
              <div className="bg-rose-950/20 border border-rose-800 text-rose-300 rounded p-3 font-mono text-xs">
                {error}
              </div>
            ) : null}
          </div>

          <button
            onClick={fetchHealth}
            disabled={loading}
            className="mt-6 w-full flex items-center justify-center gap-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-white font-mono font-semibold py-2 px-4 rounded border border-cardBorder transition duration-150"
          >
            Test Connection
          </button>
        </div>

        {/* AI Reasoning Configurations */}
        <div className="bg-cardBg border border-cardBorder rounded-lg p-5">
          <h3 className="text-sm font-bold font-mono text-white mb-4 flex items-center gap-2">
            <Cpu size={16} className="text-accentPurple" /> LLM Reasoning Config
          </h3>

          <div className="space-y-4 font-mono text-xs">
            <div className="flex justify-between items-center py-2 border-b border-cardBorder">
              <span className="text-slate-400">Active Provider</span>
              <span className="text-white font-bold bg-slate-800 border border-cardBorder rounded px-2.5 py-0.5">
                Gemini AI
              </span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-cardBorder">
              <span className="text-slate-400">Active Model</span>
              <span className="text-white font-bold bg-slate-800 border border-cardBorder rounded px-2.5 py-0.5">
                gemini-2.0-flash
              </span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-cardBorder">
              <span className="text-slate-400">Environment Verification</span>
              <span className="text-emerald-400 font-bold bg-emerald-950/40 border border-emerald-800 rounded px-2.5 py-0.5">
                LOADED
              </span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-slate-400">Graph Context Enrichment</span>
              <span className="text-emerald-400 font-bold bg-emerald-950/40 border border-emerald-800 rounded px-2.5 py-0.5">
                ENABLED (graph_context: true)
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
