import React, { useEffect, useState } from 'react';
import { Network, Search, Filter } from 'lucide-react';
import { api } from '../services/api';
import { GraphResponse, GraphNode } from '../types';
import { GraphCanvas } from '../components/GraphCanvas';
import { NodePanel } from '../components/NodePanel';

interface RepositoryMapProps {
  repositoryId: string;
  onAnalyzeImpact: (node: GraphNode) => void;
}

export const RepositoryMap: React.FC<RepositoryMapProps> = ({
  repositoryId,
  onAnalyzeImpact,
}) => {
  const [data, setData] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Selection
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  // Filters & Search
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('All');

  const fetchGraph = async () => {
    if (!repositoryId) return;
    setLoading(true);
    setError(null);
    try {
      const graph = await api.getGraph(repositoryId);
      setData(graph);
      setSelectedNode(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch code graph.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraph();
  }, [repositoryId]);

  // Filter nodes based on search and type filter dropdown
  const filteredNodes = data?.nodes.filter((n) => {
    const matchesSearch = n.name.toLowerCase().includes(search.toLowerCase()) || 
                          n.file.toLowerCase().includes(search.toLowerCase());
    const matchesType = typeFilter === 'All' || n.type === typeFilter;
    return matchesSearch && matchesType;
  }) || [];

  // Filter edges: only display edges connecting filtered nodes
  const filteredNodeIds = new Set(filteredNodes.map((n) => n.id));
  const filteredEdges = data?.edges.filter(
    (e) => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target)
  ) || [];

  if (!repositoryId) {
    return (
      <div className="bg-cardBg border border-cardBorder rounded-lg p-8 text-center text-slate-500 font-mono">
        Please select or ingest a repository on the Overview dashboard first.
      </div>
    );
  }

  return (
    <div className="space-y-4 text-sm">
      {/* Search & Filter Toolbar */}
      <div className="bg-cardBg border border-cardBorder rounded-lg p-4 flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="flex items-center gap-2">
          <Network className="text-accentPurple" size={18} />
          <h2 className="text-sm font-bold font-mono text-white">Repository Code Map</h2>
          {data && (
            <span className="text-xs text-slate-400 font-mono bg-darkBg px-2 py-0.5 border border-cardBorder rounded">
              {filteredNodes.length} nodes / {filteredEdges.length} connections
            </span>
          )}
        </div>

        <div className="flex flex-col sm:flex-row gap-3 w-full md:w-auto">
          {/* Search */}
          <div className="relative flex-1 sm:flex-none">
            <Search className="absolute left-3 top-2.5 text-slate-500" size={14} />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search code entities..."
              className="w-full sm:w-60 bg-darkBg border border-cardBorder rounded pl-9 pr-3 py-2 text-slate-200 font-mono text-xs focus:outline-none focus:border-accentPurple placeholder:opacity-50"
            />
          </div>

          {/* Type Filter */}
          <div className="relative">
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="w-full sm:w-40 bg-darkBg border border-cardBorder rounded px-3 py-2 text-slate-200 font-mono text-xs focus:outline-none focus:border-accentPurple cursor-pointer appearance-none"
            >
              <option value="All">All Types</option>
              <option value="File">Files</option>
              <option value="Class">Classes</option>
              <option value="Function">Functions</option>
              <option value="API">APIs</option>
              <option value="Test">Tests</option>
            </select>
            <Filter size={12} className="absolute right-3 top-3 text-slate-500 pointer-events-none" />
          </div>
        </div>
      </div>

      {/* Main Grid: Interactive Canvas + Inspector side panel */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-[calc(100vh-210px)]">
        {/* React Flow Canvas */}
        <div className="lg:col-span-3 h-full">
          {loading ? (
            <div className="h-full flex items-center justify-center border border-cardBorder rounded-lg bg-cardBg text-slate-500 font-mono text-xs gap-2">
              <Network className="animate-spin text-accentPurple" size={16} /> Generating Map...
            </div>
          ) : error ? (
            <div className="h-full flex items-center justify-center border border-cardBorder rounded-lg bg-cardBg p-6 text-rose-300 font-mono text-xs">
              {error}
            </div>
          ) : (
            <GraphCanvas
              nodes={filteredNodes}
              edges={filteredEdges}
              onSelectNode={setSelectedNode}
              selectedNodeId={selectedNode?.id}
            />
          )}
        </div>

        {/* Details Sidebar Panel */}
        <div className="lg:col-span-1 h-full">
          <NodePanel
            node={selectedNode}
            onClose={() => setSelectedNode(null)}
            onAnalyzeImpact={onAnalyzeImpact}
          />
        </div>
      </div>
    </div>
  );
};
