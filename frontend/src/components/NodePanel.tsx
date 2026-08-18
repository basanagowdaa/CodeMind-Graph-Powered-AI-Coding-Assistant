import React from 'react';
import { Play, Code, Tag, Hash, FileText } from 'lucide-react';
import { GraphNode } from '../types';

interface NodePanelProps {
  node: GraphNode | null;
  onClose: () => void;
  onAnalyzeImpact?: (node: GraphNode) => void;
}

export const NodePanel: React.FC<NodePanelProps> = ({
  node,
  onClose,
  onAnalyzeImpact,
}) => {
  if (!node) {
    return (
      <div className="h-full flex items-center justify-center text-slate-500 font-mono text-sm p-4 border border-dashed border-cardBorder rounded-lg">
        Click any node in the graph to view details
      </div>
    );
  }

  const hasSource = !!node.metadata.source_code;

  return (
    <div className="bg-cardBg border border-cardBorder rounded-lg p-5 h-full flex flex-col overflow-hidden text-sm relative">
      {/* Header */}
      <div className="flex items-start justify-between pb-4 border-b border-cardBorder mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-300 font-bold border border-slate-700">
              {node.type}
            </span>
            <span className="text-xs text-slate-400 font-mono flex items-center gap-1">
              <Hash size={12} /> {node.connection_count} connections
            </span>
          </div>
          <h3 className="text-base font-bold text-white font-mono break-all leading-tight">
            {node.name}
          </h3>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-white font-mono text-xs"
        >
          [Esc] Close
        </button>
      </div>

      <div className="flex-1 overflow-y-auto space-y-4 pr-1">
        {/* Entity location info */}
        {node.file && (
          <div className="bg-darkBg border border-cardBorder rounded p-2.5 font-mono text-xs text-slate-300 flex items-center gap-2">
            <FileText size={14} className="text-accentBlue" />
            <span className="truncate">{node.file}</span>
            {node.line > 0 && <span className="text-accentPurple">L{node.line}</span>}
          </div>
        )}

        {/* Function parameters / attributes */}
        {(node.metadata.parameters && node.metadata.parameters.length > 0) && (
          <div>
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
              Parameters
            </span>
            <div className="flex flex-wrap gap-1.5 font-mono text-xs">
              {node.metadata.parameters.map((p, idx) => (
                <span key={idx} className="bg-slate-800 text-slate-300 border border-slate-700 px-2 py-0.5 rounded">
                  {p}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Return type */}
        {node.metadata.return_type && (
          <div>
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
              Return Type
            </span>
            <span className="bg-slate-800 text-accentBlue border border-slate-700 font-mono text-xs px-2 py-0.5 rounded">
              {node.metadata.return_type}
            </span>
          </div>
        )}

        {/* Docstring */}
        {node.metadata.docstring && (
          <div>
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
              Docstring
            </span>
            <div className="bg-slate-900 border border-cardBorder rounded p-3 text-slate-300 italic text-xs leading-relaxed font-sans">
              {node.metadata.docstring}
            </div>
          </div>
        )}

        {/* Source code preview */}
        {hasSource && (
          <div className="flex flex-col flex-1">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1 flex items-center gap-1.5">
              <Code size={14} /> Source Snippet
            </span>
            <pre className="bg-slate-950 border border-cardBorder rounded p-3 text-xs text-slate-300 font-mono overflow-auto max-h-[300px] leading-relaxed">
              <code>{node.metadata.source_code}</code>
            </pre>
          </div>
        )}
      </div>

      {/* BEFORE YOU CHANGE IT Action */}
      {onAnalyzeImpact && (
        <div className="pt-4 border-t border-cardBorder mt-4">
          <button
            onClick={() => onAnalyzeImpact(node)}
            className="w-full flex items-center justify-center gap-2 bg-accentPurple hover:bg-violet-600 active:bg-violet-700 text-white font-mono font-semibold py-2.5 px-4 rounded transition duration-150 shadow-lg shadow-violet-900/30"
          >
            <Play size={14} fill="currentColor" /> BEFORE YOU CHANGE IT
          </button>
        </div>
      )}
    </div>
  );
};
