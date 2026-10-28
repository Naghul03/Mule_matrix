import React, { useEffect, useRef } from 'react';
import cytoscape, { Core } from 'cytoscape';
// @ts-ignore
import coseBilkent from 'cytoscape-cose-bilkent';
import { ZoomIn, ZoomOut, Maximize2, RefreshCw } from 'lucide-react';

try {
  cytoscape.use(coseBilkent);
} catch {
  // Already registered
}

export interface GraphEntityNode {
  id: string;
  label: string;
  subLabel?: string;
  isVictim?: boolean;
  isSuspicious?: boolean;
  bankCode?: string;
  riskScore?: number;
}

export interface GraphEntityEdge {
  id: string;
  source: string;
  target: string;
  amount: number;
  label: string;
  isSuspicious?: boolean;
  timestamp?: string;
}

interface NetworkGraphProps {
  nodes: GraphEntityNode[];
  edges: GraphEntityEdge[];
  selectedId: string | null;
  onSelectNode: (node: GraphEntityNode | null) => void;
  onSelectEdge?: (edge: GraphEntityEdge | null) => void;
}

export const NetworkGraph: React.FC<NetworkGraphProps> = ({
  nodes,
  edges,
  selectedId,
  onSelectNode,
  onSelectEdge,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const cyElements = [
      ...nodes.map((n) => ({
        data: {
          id: n.id,
          label: n.label,
          subLabel: n.subLabel || '',
          isVictim: n.isVictim ? 'yes' : 'no',
          isSuspicious: n.isSuspicious ? 'yes' : 'no',
          raw: n,
        },
        classes: `${n.isVictim ? 'victim' : ''} ${n.isSuspicious ? 'suspicious' : ''} ${selectedId === n.id ? 'selected' : ''}`,
      })),
      ...edges.map((e) => ({
        data: {
          id: e.id,
          source: e.source,
          target: e.target,
          label: e.label,
          isSuspicious: e.isSuspicious ? 'yes' : 'no',
          raw: e,
        },
        classes: `${e.isSuspicious ? 'suspicious' : ''} ${selectedId === e.id ? 'selected' : ''}`,
      })),
    ];

    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements: cyElements,
      boxSelectionEnabled: false,
      autounselectify: false,
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'color': '#F1EDE5',
            'font-family': 'Inter, sans-serif',
            'font-size': '10px',
            'font-weight': 600,
            'text-valign': 'center',
            'text-halign': 'center',
            'background-color': '#1E1B15',
            'border-width': 2,
            'border-color': '#6C5636',
            'width': 42,
            'height': 42,
            'text-wrap': 'wrap',
          },
        },
        {
          selector: 'node.victim',
          style: {
            'background-color': '#211C14',
            'border-color': '#82796B',
            'border-style': 'dashed',
            'color': '#B8B0A2',
          },
        },
        {
          selector: 'node.suspicious',
          style: {
            'background-color': '#281714',
            'border-color': '#B85C50',
            'border-width': 2.5,
          },
        },
        {
          selector: 'node.selected',
          style: {
            'border-color': '#B99D73',
            'border-width': 3,
            'background-color': '#2B2318',
          },
        },
        {
          selector: 'edge',
          style: {
            'width': 2,
            'line-color': '#51422E',
            'target-arrow-color': '#51422E',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'arrow-scale': 1.1,
            'label': 'data(label)',
            'color': '#B8B0A2',
            'font-size': '9.5px',
            'font-family': 'JetBrains Mono, monospace',
            'font-weight': 500,
            'text-rotation': 'autorotate',
            'text-background-color': '#12110E',
            'text-background-opacity': 0.9,
            'text-background-padding': '3px',
            'text-background-shape': 'roundrectangle',
          },
        },
        {
          selector: 'edge.suspicious',
          style: {
            'line-color': '#B85C50',
            'target-arrow-color': '#B85C50',
            'width': 2.5,
            'color': '#F1EDE5',
          },
        },
        {
          selector: 'edge.selected',
          style: {
            'line-color': '#B99D73',
            'target-arrow-color': '#B99D73',
            'width': 3,
            'color': '#B99D73',
          },
        },
      ],
      layout: {
        name: 'breadthfirst',
        directed: true,
        padding: 40,
        spacingFactor: 1.25,
      },
    });

    cy.on('tap', 'node', (evt) => {
      const nodeData = evt.target.data('raw');
      onSelectNode(nodeData);
    });

    cy.on('tap', 'edge', (evt) => {
      const edgeData = evt.target.data('raw');
      if (onSelectEdge) onSelectEdge(edgeData);
    });

    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        onSelectNode(null);
        if (onSelectEdge) onSelectEdge(null);
      }
    });

    cyRef.current = cy;

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
      }
    };
  }, [nodes, edges, selectedId]);

  const handleZoomIn = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.2);
  const handleZoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() * 0.8);
  const handleFit = () => cyRef.current?.fit(undefined, 30);
  const handleResetLayout = () => {
    cyRef.current?.layout({ name: 'breadthfirst', directed: true, padding: 40, spacingFactor: 1.25 }).run();
  };

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', minHeight: '340px' }}>
      {/* Floating Canvas Controls */}
      <div
        style={{
          position: 'absolute',
          bottom: '12px',
          right: '12px',
          zIndex: 10,
          display: 'flex',
          gap: '6px',
        }}
      >
        <button onClick={handleZoomIn} className="mm-btn-icon" title="Zoom In">
          <ZoomIn style={{ width: '13px', height: '13px' }} />
        </button>
        <button onClick={handleZoomOut} className="mm-btn-icon" title="Zoom Out">
          <ZoomOut style={{ width: '13px', height: '13px' }} />
        </button>
        <button onClick={handleFit} className="mm-btn-icon" title="Fit to Viewport">
          <Maximize2 style={{ width: '13px', height: '13px' }} />
        </button>
        <button onClick={handleResetLayout} className="mm-btn-icon" title="Reset Layout">
          <RefreshCw style={{ width: '13px', height: '13px' }} />
        </button>
      </div>

      <div ref={containerRef} style={{ width: '100%', height: '100%', minHeight: '340px' }} />
    </div>
  );
};
