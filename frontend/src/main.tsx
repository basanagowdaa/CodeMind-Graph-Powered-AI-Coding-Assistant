import React, { useState } from 'react';
import ReactDOM from 'react-dom/client';
import { Layout, Cpu, Network, Play, Search as SearchIcon, Settings as SettingsIcon, BarChart2, ShieldAlert } from 'lucide-react';

import './index.css';
import { Overview } from './pages/Overview';
import { RepositoryMap } from './pages/RepositoryMap';
import { AskCodeMind } from './pages/AskCodeMind';
import { ImpactAnalysis } from './pages/ImpactAnalysis';
import { Search } from './pages/Search';
import { Settings } from './pages/Settings';
import { Benchmark } from './pages/Benchmark';
import { StatusBadge } from './components/StatusBadge';
import { GraphNode } from './types';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'overview' | 'map' | 'ask' | 'impact' | 'search' | 'settings' | 'benchmark'>('overview');
  const [selectedRepositoryId, setSelectedRepositoryId] = useState('');
  
  // Cross-page state mapping: selected entity for BEFORE YOU CHANGE IT
  const [selectedEntity, setSelectedEntity] = useState<GraphNode | null>(null);

  const handleSelectNodeFromMap = (node: GraphNode) => {
    setSelectedEntity(node);
  };

  const handleSelectNodeFromSearch = (nodeId: string) => {
    // Search only gives us ID, page will fetch graph and resolve, but we can set placeholder
    setSelectedEntity({
      id: nodeId,
      name: nodeId.split(':')[1] || nodeId,
      type: nodeId.split(':')[0] || 'Function',
      file: '',
      line: 0,
      connection_count: 0,
      label: nodeId.split(':')[1] || nodeId,
      metadata: {},
    });
  };

  const handleAnalyzeImpact = (node: GraphNode) => {
    setSelectedEntity(node);
    setActiveTab('impact');
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Navbar Header */}
      <header className="bg-cardBg border-b border-cardBorder px-6 py-4 flex items-center justify-between shadow-md relative z-10">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-accentPurple/20 border border-accentPurple/40 rounded-lg text-accentPurple shadow-inner shadow-violet-950/20">
            <Cpu size={22} className="animate-pulse" />
          </div>
          <div>
            <h1 className="text-base font-bold font-mono text-white tracking-wider flex items-center gap-1.5">
              CodeMind <span className="text-[10px] bg-accentPurple px-1.5 py-0.5 rounded text-white font-normal scale-90 uppercase">V2</span>
            </h1>
            <span className="text-[10px] font-mono text-slate-500 block">
              Graph-Powered AI Coding Assistant
            </span>
          </div>
        </div>

        {/* Real-time Status Badge */}
        <StatusBadge />
      </header>

      {/* Main Container */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar Navigation */}
        <aside className="w-60 bg-cardBg border-r border-cardBorder flex flex-col justify-between p-4 shrink-0 font-mono text-xs select-none">
          <nav className="space-y-1">
            <button
              onClick={() => setActiveTab('overview')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded transition ${
                activeTab === 'overview'
                  ? 'bg-accentPurple/15 text-white border border-accentPurple/30 font-bold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/40 border border-transparent'
              }`}
            >
              <Layout size={16} /> Overview
            </button>

            <button
              onClick={() => setActiveTab('map')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded transition ${
                activeTab === 'map'
                  ? 'bg-accentPurple/15 text-white border border-accentPurple/30 font-bold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/40 border border-transparent'
              }`}
            >
              <Network size={16} /> Repository Map
            </button>

            <button
              onClick={() => setActiveTab('ask')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded transition ${
                activeTab === 'ask'
                  ? 'bg-accentPurple/15 text-white border border-accentPurple/30 font-bold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/40 border border-transparent'
              }`}
            >
              <Cpu size={16} /> Ask CodeMind
            </button>

            <button
              onClick={() => setActiveTab('impact')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded transition ${
                activeTab === 'impact'
                  ? 'bg-accentPurple/15 text-white border border-accentPurple/30 font-bold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/40 border border-transparent'
              }`}
            >
              <Play size={16} fill={activeTab === 'impact' ? 'currentColor' : 'none'} /> Impact Analysis
            </button>

            <button
              onClick={() => setActiveTab('search')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded transition ${
                activeTab === 'search'
                  ? 'bg-accentPurple/15 text-white border border-accentPurple/30 font-bold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/40 border border-transparent'
              }`}
            >
              <SearchIcon size={16} /> Code Search
            </button>

            <button
              onClick={() => setActiveTab('benchmark')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded transition ${
                activeTab === 'benchmark'
                  ? 'bg-accentPurple/15 text-white border border-accentPurple/30 font-bold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/40 border border-transparent'
              }`}
            >
              <BarChart2 size={16} /> Benchmarking
            </button>
          </nav>

          <nav className="space-y-1">
            <button
              onClick={() => setActiveTab('settings')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded transition ${
                activeTab === 'settings'
                  ? 'bg-accentPurple/15 text-white border border-accentPurple/30 font-bold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/40 border border-transparent'
              }`}
            >
              <SettingsIcon size={16} /> Settings
            </button>
            <div className="px-3 py-2 text-[10px] text-slate-500 font-mono border-t border-cardBorder mt-4">
              <span>Hack Hydra 2026</span>
            </div>
          </nav>
        </aside>

        {/* Dynamic Page Viewer */}
        <main className="flex-1 overflow-y-auto p-6 bg-darkBg">
          {activeTab === 'overview' && (
            <Overview
              onSelectRepository={setSelectedRepositoryId}
              selectedRepositoryId={selectedRepositoryId}
            />
          )}

          {activeTab === 'map' && (
            <RepositoryMap
              repositoryId={selectedRepositoryId}
              onAnalyzeImpact={handleAnalyzeImpact}
            />
          )}

          {activeTab === 'ask' && (
            <AskCodeMind repositoryId={selectedRepositoryId} />
          )}

          {activeTab === 'impact' && (
            <ImpactAnalysis
              repositoryId={selectedRepositoryId}
              selectedEntity={selectedEntity}
              onClearEntity={() => setSelectedEntity(null)}
            />
          )}

          {activeTab === 'search' && (
            <Search
              repositoryId={selectedRepositoryId}
              onSelectNode={handleSelectNodeFromSearch}
              onNavigateToMap={() => setActiveTab('map')}
            />
          )}

          {activeTab === 'benchmark' && (
            <Benchmark repositoryId={selectedRepositoryId} />
          )}

          {activeTab === 'settings' && <Settings />}
        </main>
      </div>
    </div>
  );
};

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
export default App;
