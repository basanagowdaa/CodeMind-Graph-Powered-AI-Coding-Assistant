import React, { useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node as FlowNode,
  Edge as FlowEdge,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';

import { GraphNode, GraphEdge } from '../types';

interface GraphCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onSelectNode: (node: GraphNode) => void;
  selectedNodeId?: string;
}

// Color maps by node type
const TYPE_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  File: { bg: '#1e293b', border: '#475569', text: '#94a3b8' },
  Class: { bg: '#1d4ed8', border: '#3b82f6', text: '#dbeafe' },
  Function: { bg: '#6d28d9', border: '#8b5cf6', text: '#f3e8ff' },
  API: { bg: '#047857', border: '#10b981', text: '#ecfdf5' },
  Test: { bg: '#be185d', border: '#ec4899', text: '#fce7f3' },
  default: { bg: '#1f293d', border: '#4b5563', text: '#f8fafc' },
};

export const GraphCanvas: React.FC<GraphCanvasProps> = ({
  nodes,
  edges,
  onSelectNode,
  selectedNodeId,
}) => {
  // Map our node models to React Flow Nodes
  const flowNodes = useMemo<FlowNode[]>(() => {
    // Basic grid positioning
    const cols = 5;
    return nodes.map((n, i) => {
      const colors = TYPE_COLORS[n.type] || TYPE_COLORS.default;
      const isSelected = n.id === selectedNodeId;

      // Scale node size by connection count (between 0.8x and 1.6x)
      const scale = Math.min(1.6, 0.8 + (n.connection_count * 0.05));
      const sizeStyle = {
        transform: `scale(${scale})`,
        transformOrigin: 'center',
      };

      return {
        id: n.id,
        type: 'default',
        data: {
          label: (
            <div className="flex flex-col items-center justify-center text-center p-1 font-mono">
              <span className="text-[10px] opacity-60 font-semibold tracking-wider uppercase">
                {n.type}
              </span>
              <span className="text-xs font-bold truncate max-w-[150px]">
                {n.label}
              </span>
            </div>
          ),
        },
        position: {
          x: (i % cols) * 260 + 50,
          y: Math.floor(i / cols) * 160 + 50,
        },
        style: {
          background: colors.bg,
          color: colors.text,
          border: isSelected ? '2px solid #a78bfa' : `1px solid ${colors.border}`,
          boxShadow: isSelected ? '0 0 15px rgba(139, 92, 246, 0.6)' : 'none',
          padding: '8px',
          width: 170,
          borderRadius: '8px',
          cursor: 'pointer',
          transition: 'all 0.2s ease',
          ...sizeStyle,
        },
      };
    });
  }, [nodes, selectedNodeId]);

  // Map our edge models to React Flow Edges
  const flowEdges = useMemo<FlowEdge[]>(() => {
    return edges.map((e, i) => {
      const isCall = e.relationship === 'CALLS';
      const isTest = e.relationship === 'TESTS';
      
      let strokeColor = '#4b5563'; // default gray
      if (isCall) strokeColor = '#8b5cf6'; // purple calls
      if (isTest) strokeColor = '#ec4899'; // pink tests

      return {
        id: `edge-${i}-${e.source}-${e.target}`,
        source: e.source,
        target: e.target,
        label: e.relationship,
        labelStyle: { fill: '#94a3b8', fontSize: 8, fontFamily: 'monospace', fontWeight: 500 },
        labelBgPadding: [4, 2],
        labelBgBorderRadius: 4,
        labelBgStyle: { fill: '#131926', fillOpacity: 0.8 },
        animated: isCall || isTest,
        style: {
          stroke: strokeColor,
          strokeWidth: isCall || isTest ? 2 : 1.2,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 10,
          height: 10,
          color: strokeColor,
        },
      };
    });
  }, [edges]);

  // Handle clicking on a node
  const onNodeClick = (_event: React.MouseEvent, node: FlowNode) => {
    const originalNode = nodes.find((n) => n.id === node.id);
    if (originalNode) {
      onSelectNode(originalNode);
    }
  };

  return (
    <div className="w-full h-full border border-cardBorder rounded-lg overflow-hidden bg-darkBg relative">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        onNodeClick={onNodeClick}
        fitView
        minZoom={0.2}
        maxZoom={2}
      >
        <Background color="#1f293d" gap={16} size={1} />
        <Controls showInteractive={false} />
        <MiniMap
          nodeColor={(node) => {
            // Match mini-map node colors
            return '#8b5cf6';
          }}
          maskColor="rgba(11, 15, 25, 0.6)"
          style={{ background: '#131926', border: '1px solid #1f293d' }}
        />
      </ReactFlow>
    </div>
  );
};
