import React, { useEffect, useState } from 'react';
import { ShieldCheck, ShieldAlert, Database, RefreshCw } from 'lucide-react';
import { api } from '../services/api';
import { ConnectionStatus } from '../types';

export const StatusBadge: React.FC = () => {
  const [status, setStatus] = useState<ConnectionStatus>({
    connected: false,
    message: 'Checking connection...',
  });
  const [loading, setLoading] = useState(false);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const data = await api.getHealth();
      setStatus(data);
    } catch {
      setStatus({
        connected: false,
        message: 'Could not connect to backend server.',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    // Poll connection status every 30 seconds
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const isConnected = status.connected;

  return (
    <div
      className={`flex items-center gap-2.5 px-3 py-1.5 rounded-full border text-xs font-mono transition-all duration-300 ${
        isConnected
          ? 'bg-emerald-950/40 border-emerald-800 text-emerald-300'
          : 'bg-rose-950/40 border-rose-800 text-rose-300'
      }`}
      title={status.message}
    >
      <div className="relative flex h-2 w-2">
        {isConnected && (
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
        )}
        <span
          className={`relative inline-flex rounded-full h-2 w-2 ${
            isConnected ? 'bg-emerald-400' : 'bg-rose-500'
          }`}
        ></span>
      </div>

      <div className="flex items-center gap-1.5">
        <Database size={12} />
        <span className="font-semibold select-none">
          {isConnected ? 'HydraDB Connected' : 'HydraDB Disconnected'}
        </span>
        {status.databases_count !== undefined && isConnected && (
          <span className="opacity-60 bg-emerald-900/60 border border-emerald-800 rounded px-1.5 text-[10px] scale-90">
            {status.databases_count} DBs
          </span>
        )}
      </div>

      <button
        onClick={fetchStatus}
        disabled={loading}
        className={`hover:text-white p-0.5 rounded transition ${loading ? 'animate-spin' : ''}`}
        aria-label="Refresh status"
      >
        <RefreshCw size={12} />
      </button>
    </div>
  );
};
