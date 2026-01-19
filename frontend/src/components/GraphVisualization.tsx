import { useState, useEffect, useCallback } from 'react';
import { 
  ReactFlow, 
  Controls, 
  Background,
  BackgroundVariant,
  Panel,
  type Node,
  type Edge,
  useNodesState,
  useEdgesState
} from '@xyflow/react';
import dagre from 'dagre';
import '@xyflow/react/dist/style.css';
import './GraphVisualization.css';

interface GraphVisualizationProps {
  graphData: any; // JSON structure from API
}

// Dagre layout helper
const getLayoutedElements = (nodes: Node[], edges: Edge[], direction = 'TB') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: direction, nodesep: 100, ranksep: 150 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 180, height: 80 });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - 90,
        y: nodeWithPosition.y - 40,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

export function GraphVisualization({ graphData }: GraphVisualizationProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [loading, setLoading] = useState(false);
  const [clusters, setClusters] = useState<any[]>([]);
  const [selectedCluster, setSelectedCluster] = useState<number | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Fullscreen toggle
  const toggleFullscreen = useCallback(() => {
    const container = document.querySelector('.graph-container');
    if (!container) return;

    if (!document.fullscreenElement) {
      container.requestFullscreen().then(() => {
        setIsFullscreen(true);
      }).catch((err) => {
        console.error('Fullscreen error:', err);
      });
    } else {
      document.exitFullscreen().then(() => {
        setIsFullscreen(false);
      });
    }
  }, []);

  // Listen for fullscreen changes (e.g., ESC key)
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);

  // NEAT: knowledge states graph
  const convertNEATToFlow = (data: any, clusterFilter: number | null = null) => {
    const flowNodes: Node[] = [];
    const flowEdges: Edge[] = [];
    
    let nodeId = 0;
    const stateToId: { [key: string]: string } = {};

    // Handle structured output from clustered mode
    let graphData;
    if (clusterFilter !== null && data?.clusters && data.clusters[clusterFilter]) {
      // Use specific cluster
      graphData = data.clusters[clusterFilter].learning_space || {};
    } else {
      // Use merged or raw data
      graphData = data?.merged_learning_space || data?.learning_space || data;
    }
    
    if (!graphData || typeof graphData !== 'object') {
      return { nodes: flowNodes, edges: flowEdges };
    }

    // Create nodes for each knowledge state (capped at 100 for better visibility)
    const states = Object.keys(graphData).slice(0, 100);
    states.forEach((state) => {
      const id = `node-${nodeId++}`;
      stateToId[state] = id;

      const isEmpty = state === '{}' || state === '∅';
      const itemCount = state.split(',').filter(s => s.trim() && s !== '{}').length;
      
      // Short label for display
      const shortLabel = isEmpty ? '∅' : itemCount === 1 
        ? state.replace(/[{}]/g, '').trim()
        : `${itemCount} items`;
      
      // Expanded label for hover - prikazuje sve iteme
      const items = state.replace(/[{}]/g, '').split(',').filter((s: string) => s.trim());
      const expandedLabel = isEmpty ? 'Empty State (∅)' : items.map(item => item.trim()).join('\n');
      
      flowNodes.push({
        id,
        data: { 
          label: shortLabel,
          fullState: state,
          itemCount: itemCount,
          expandedLabel: expandedLabel,
          shortLabel: shortLabel
        },
        position: { x: 0, y: 0 }, // Will be set by dagre
        style: {
          background: isEmpty 
            ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' 
            : `linear-gradient(135deg, ${itemCount > 5 ? '#f093fb 0%, #f5576c 100%' : '#4facfe 0%, #00f2fe 100%'})`,
          border: '3px solid',
          borderColor: isEmpty ? '#5a67d8' : itemCount > 5 ? '#ec4899' : '#0ea5e9',
          borderRadius: '12px',
          padding: '12px 20px',
          fontSize: '14px',
          fontWeight: '600',
          color: '#ffffff',
          boxShadow: '0 4px 8px rgba(0, 0, 0, 0.3)',
          minWidth: '100px',
          maxWidth: '300px',
          textAlign: 'center',
          cursor: 'pointer',
          whiteSpace: 'pre-line',
          wordBreak: 'break-word'
        },
      });
    });

    // Create edges between states
    states.forEach((source) => {
      const targets = graphData[source] || [];
      const sourceId = stateToId[source];
      (targets as string[]).forEach((target) => {
        if (stateToId[target]) {
          flowEdges.push({
            id: `${sourceId}-${stateToId[target]}`,
            source: sourceId,
            target: stateToId[target],
            type: 'smoothstep',
            style: { 
              stroke: '#8b5cf6', 
              strokeWidth: 2,
              opacity: 0.6
            },
            markerEnd: {
              type: 'arrowclosed',
              color: '#8b5cf6'
            }
          });
        }
      });
    });

    // Apply dagre layout for hierarchical view
    return getLayoutedElements(flowNodes, flowEdges);
  };

  // Extract clusters from structured output
  useEffect(() => {
    if (graphData?.clusters) {
      setClusters(graphData.clusters);
    }
  }, [graphData]);

  // Initialize graph when data changes (deferred to prevent blocking UI)
  useEffect(() => {
    if (!graphData) return;

    setLoading(true);
    // Defer heavy conversion to next tick to avoid blocking UI on large graphs
    const timer = setTimeout(() => {
      const { nodes: flowNodes, edges: flowEdges } = convertNEATToFlow(graphData, selectedCluster);
      
      setNodes(flowNodes);
      setEdges(flowEdges);
      setLoading(false);
    }, 0);

    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graphData, selectedCluster]);

  // Node hover handlers - menjaju label
  const onNodeMouseEnter = useCallback((_event: any, node: Node) => {
    setNodes((nds) =>
      nds.map((n) => {
        if (n.id === node.id) {
          return {
            ...n,
            data: {
              ...n.data,
              label: n.data.expandedLabel || n.data.label
            }
          };
        }
        return n;
      })
    );
  }, [setNodes]);

  const onNodeMouseLeave = useCallback((_event: any, node: Node) => {
    setNodes((nds) =>
      nds.map((n) => {
        if (n.id === node.id) {
          return {
            ...n,
            data: {
              ...n.data,
              label: n.data.shortLabel || n.data.label
            }
          };
        }
        return n;
      })
    );
  }, [setNodes]);

  return (
    <div className="graph-visualization">
      <div className="graph-header">
        <h2>Knowledge Space</h2>
        <p className="graph-info">
          {nodes.length} nodes, {edges.length} edges
          {nodes.length >= 500 && <span> (capped at 500 for performance)</span>}
          {loading && <span> · Loading...</span>}
        </p>
      </div>
      
      <div className="graph-container">
        {loading && (
          <div className="graph-loading">
            <div className="spinner" />
            <p>Processing graph...</p>
          </div>
        )}
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeMouseEnter={onNodeMouseEnter}
          onNodeMouseLeave={onNodeMouseLeave}
          fitView
          fitViewOptions={{ padding: 0.3, maxZoom: 1.5 }}
          minZoom={0.2}
          maxZoom={2}
          defaultViewport={{ x: 0, y: 0, zoom: 1 }}
          style={{ opacity: loading ? 0.5 : 1 }}
          attributionPosition="bottom-right"
        >
          <Background 
            variant={BackgroundVariant.Dots} 
            gap={20} 
            size={2} 
            color="rgba(148, 163, 184, 0.2)" 
          />
          <Controls 
            showZoom={true}
            showFitView={true}
            showInteractive={true}
          />
          {clusters.length > 0 && (
            <Panel position="top-left" className="cluster-filter-panel">
              <div style={{ background: 'rgba(30, 41, 59, 0.95)', padding: '12px', borderRadius: '8px', minWidth: '200px' }}>
                <h4 style={{ margin: '0 0 8px 0', fontSize: '14px', color: '#e2e8f0' }}>Filter by Cluster</h4>
                <select 
                  value={selectedCluster ?? 'all'} 
                  onChange={(e) => setSelectedCluster(e.target.value === 'all' ? null : Number(e.target.value))}
                  style={{ width: '100%', padding: '6px', borderRadius: '4px', background: '#1e293b', color: '#e2e8f0', border: '1px solid #475569' }}
                >
                  <option value="all">All Clusters (merged)</option>
                  {clusters.map((cluster, idx) => (
                    <option key={idx} value={cluster.cluster_id}>
                      Cluster {cluster.cluster_id + 1} ({cluster.num_items} items)
                    </option>
                  ))}
                </select>
              </div>
            </Panel>
          )}
          <Panel position="top-right" className="graph-controls-panel">
            <button 
              onClick={toggleFullscreen}
              className="fullscreen-btn"
              title={isFullscreen ? 'Exit Fullscreen (ESC)' : 'Enter Fullscreen'}
            >
              {isFullscreen ? (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" />
                </svg>
              ) : (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
                </svg>
              )}
            </button>
          </Panel>
          <Panel position="bottom-right" className="graph-legend">
            <div className="legend-content">
              <div className="legend-item">
                <span className="legend-color" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', border: '2px solid #5a67d8' }}></span>
                Empty State (∅)
              </div>
              <div className="legend-item">
                <span className="legend-color" style={{ background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', border: '2px solid #0ea5e9' }}></span>
                Simple States (&le;5 items)
              </div>
              <div className="legend-item">
                <span className="legend-color" style={{ background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', border: '2px solid #ec4899' }}></span>
                Complex States (&gt;5 items)
              </div>
            </div>
          </Panel>
        </ReactFlow>
      </div>
    </div>
  );
}
