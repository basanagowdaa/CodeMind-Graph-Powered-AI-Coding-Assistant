import React, { useState } from 'react';
import { Search as SearchIcon, FileCode, Play, ListCollapse, Database } from 'lucide-react';
import { api } from '../services/api';

interface SearchProps {
  repositoryId: string;
  onSelectNode: (nodeId: string) => void;
  onNavigateToMap: () => void;
}

export const Search: React.FC<SearchProps> = ({
  repositoryId,
  onSelectNode,
  onNavigateToMap,
}) => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || loading || !repositoryId) return;

    setLoading(true);
    setError(null);
    try {
      // Direct graph search via local graph filter
      const graph = await api.getGraph(repositoryId);
      const matched = graph.nodes.filter(
        (n) =>
          n.name.toLowerCase().includes(query.toLowerCase()) ||
          n.file.toLowerCase().includes(query.toLowerCase()) ||
          (n.metadata?.docstring && n.metadata.docstring.toLowerCase().includes(query.toLowerCase()))
      );
      setResults(matched);
    } catch (err: any) {
      setError(err.message || 'Failed to search repository.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectNode = (nodeId: string) => {
    onSelectNode(nodeId);
    onNavigateToMap();
  };

  if (!repositoryId) {
    return (
      <div className="bg-cardBg border border-cardBorder rounded-lg p-8 text-center text-slate-500 font-mono">
        Please select or ingest a repository on the Overview dashboard first.
      </div>
    );
  }

  return (
    <div className="space-y-6 text-sm">
      {/* Search Header */}
      <div className="bg-cardBg border border-cardBorder rounded-lg p-5">
        <h2 className="text-base font-bold font-mono text-white mb-2 flex items-center gap-2">
          <SearchIcon size={18} className="text-accentPurple" /> Code Entity Finder
        </h2>
        <p className="text-slate-400 text-xs mb-4">
          Find functions, classes, APIs, or test files in the repository index. Clicking a result navigates to its location on the Code Map.
        </p>

        <form onSubmit={handleSearch} className="flex gap-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search function names, file paths, class fields..."
            className="flex-1 bg-darkBg border border-cardBorder rounded px-4 py-2.5 text-slate-200 font-mono text-xs focus:outline-none focus:border-accentPurple placeholder:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="bg-accentPurple hover:bg-violet-600 active:bg-violet-700 disabled:opacity-50 text-white font-mono font-semibold py-2 px-5 rounded transition duration-150"
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </form>
      </div>

      {error && (
        <div className="bg-rose-950/20 border border-rose-800 text-rose-300 rounded p-4 font-mono text-xs">
          {error}
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div className="bg-cardBg border border-cardBorder rounded-lg p-5">
          <h3 className="text-sm font-bold font-mono text-white mb-3">
            Search Results ({results.length} Found)
          </h3>
          <div className="space-y-3">
            {results.map((r) => (
              <div
                key={r.id}
                onClick={() => handleSelectNode(r.id)}
                className="bg-darkBg border border-cardBorder hover:border-slate-700 rounded p-4 cursor-pointer transition flex items-start justify-between font-mono text-xs"
              >
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-white font-bold text-sm">
                      {r.name}{r.type === 'Function' ? '()' : ''}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[9px] uppercase font-bold bg-slate-900 border border-cardBorder text-slate-500">
                      {r.type}
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-500 block truncate max-w-xl">
                    File: {r.file} {r.line > 0 && `(Line ${r.line})`}
                  </span>
                  {r.metadata?.docstring && (
                    <p className="text-[11px] text-slate-400 font-sans italic mt-1.5 line-clamp-2">
                      &quot;{r.metadata.docstring}&quot;
                    </p>
                  )}
                </div>
                <span className="text-accentPurple hover:underline text-[10px] self-center shrink-0">
                  Inspect in Map →
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {results.length === 0 && query && !loading && (
        <div className="bg-cardBg border border-cardBorder rounded-lg p-6 text-center text-slate-500 font-mono">
          No matches found for &quot;{query}&quot;. Try adjusting your query terms.
        </div>
      )}
    </div>
  );
};
