import React, { useEffect, useMemo, useState, useCallback } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  Panel,
  Handle,
  Position,
  ReactFlowProvider,
  useReactFlow,
  type Node,
  type NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import ELK from 'elkjs/lib/elk.bundled.js';

import { Box, Paper, Typography, CircularProgress, Alert, Button, Stack, Chip, Tooltip } from '@mui/material';
import { parseKnowledgeSpace, type ParsedGraph, type KnowledgeNodeData } from '../utils/graphParser';
import { useProgressiveGraph } from '../hooks/useProgressiveGraph';

// Initialize ELK - it handles its own internal workers
const elk = new ELK();

// --- Custom Node ---
const KnowledgeNode = ({ data, selected }: NodeProps<Node<KnowledgeNodeData>>) => {
  // Color based on level (gradient or distinct colors)
  const levelColors = ['#1976d2', '#1565c0', '#0d47a1', '#002171'];
  const baseColor = levelColors[Math.min(data.level, levelColors.length - 1)] || '#1976d2';
  
  const tooltipTitle = (
    <div style={{ maxWidth: '400px' }}>
      <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
        {data.fullLabel}
      </Typography>
      <Typography variant="caption" display="block">
        Level: {data.level}
      </Typography>
      <Typography variant="caption" display="block">
        Concepts: {data.conceptCount}
      </Typography>
    </div>
  );

  return (
    <Tooltip 
      title={tooltipTitle}
      arrow
      placement="top"
      enterDelay={300}
      leaveDelay={100}
    >
      <div
        style={{
          padding: '10px',
          borderRadius: '5px',
          border: selected ? '2px solid #ff9800' : '1px solid #777',
          backgroundColor: '#fff',
          color: '#333',
          minWidth: '100px',
          textAlign: 'center',
          boxShadow: selected ? '0 0 10px rgba(255, 152, 0, 0.5)' : '0 2px 5px rgba(0,0,0,0.1)',
          position: 'relative',
          fontSize: '12px',
        }}
      >
        <Handle type="target" position={Position.Top} style={{ background: '#555' }} />
        
        <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>{data.label}</div>
        {data.fullLabel !== data.label && (
           <div style={{ 
             fontSize: '10px', 
             color: '#666', 
             overflow: 'hidden', 
             textOverflow: 'ellipsis', 
             whiteSpace: 'nowrap' 
           }}>
              {data.fullLabel}
           </div>
        )}
        
        <div
          style={{
            position: 'absolute',
            top: '-8px',
            right: '-8px',
            background: baseColor,
            color: 'white',
            borderRadius: '50%',
            width: '20px',
            height: '20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '10px',
            fontWeight: 'bold',
          }}
          title={`Level: ${data.level}, Concepts: ${data.conceptCount}`}
        >
          {data.level}
        </div>

        <Handle type="source" position={Position.Bottom} style={{ background: '#555' }} />
      </div>
    </Tooltip>
  );
};

// Cluster node for collapsed levels
const ClusterNode = ({ data }: NodeProps) => {
  const clusterData = data as any;
  return (
    <div
      style={{
        padding: '15px 20px',
        borderRadius: '8px',
        border: '2px dashed #757575',
        backgroundColor: '#f5f5f5',
        color: '#333',
        minWidth: '150px',
        textAlign: 'center',
        cursor: 'pointer',
        boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: '#757575' }} />
      
      <div style={{ fontSize: '24px', marginBottom: '8px' }}>📦</div>
      <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>{String(clusterData.label)}</div>
      <div style={{ fontSize: '11px', color: '#666' }}>
        {clusterData.childCount} nodes
      </div>
      <div style={{ fontSize: '10px', color: '#999', marginTop: '8px' }}>
        Click to expand
      </div>

      <Handle type="source" position={Position.Bottom} style={{ background: '#757575' }} />
    </div>
  );
};

const nodeTypes = {
  default: KnowledgeNode,
  cluster: ClusterNode,
};

// --- Main Component ---

interface KnowledgeSpaceGraphProps {
  knowledgeSpace: Record<string, string[]>;
}

const GraphInner: React.FC<KnowledgeSpaceGraphProps> = ({ knowledgeSpace }) => {
  const [nodes, setNodes, onNodesChange] = useNodesState<any>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<any>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { fitView } = useReactFlow();
  
  // Memoize parsing to avoid re-parsing on every render
  const parsedGraph = useMemo<ParsedGraph>(() => parseKnowledgeSpace(knowledgeSpace), [knowledgeSpace]);

  // Progressive loading hook
  const {
    visibleNodes,
    visibleEdges,
    expandedLevels,
    maxLevel,
    toggleLevel,
    expandAll,
    collapseAll,
    nodesByLevel,
  } = useProgressiveGraph(parsedGraph);

  // Handle node clicks for clusters
  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    if (node.type === 'cluster') {
      // Extract level from cluster id: "cluster-level-3" -> 3
      const levelMatch = node.id.match(/cluster-level-(\d+)/);
      if (levelMatch) {
        const level = parseInt(levelMatch[1], 10);
        toggleLevel(level);
      }
    }
  }, [toggleLevel]);

  useEffect(() => {
    let cancelled = false;

    const runLayout = async () => {
      setLoading(true);
      setError(null);

      // Initial check
      if (visibleNodes.length === 0) {
        setNodes([]);
        setEdges([]);
        setLoading(false);
        return;
      }

      // Prepare graph for ELK layout with visible nodes only
      const graph = {
        id: 'root',
        layoutOptions: {
          'elk.algorithm': 'layered',
          'elk.direction': 'DOWN',
          'elk.layered.nodePlacement.strategy': 'BRANDES_KOEPF',
          'elk.spacing.nodeNode': '50',
          'elk.layered.spacing.nodeNodeBetweenLayers': '80',
          'elk.edgeRouting': 'SPLINES',
        },
        children: visibleNodes.map(node => ({
          id: node.id,
          width: node.type === 'cluster' ? 180 : 150,
          height: node.type === 'cluster' ? 100 : 60,
        })),
        edges: visibleEdges.map(edge => ({
          id: edge.id,
          sources: [edge.source],
          targets: [edge.target],
        })),
      };

      try {
        // ELK.layout() is async and uses internal workers automatically
        const layoutedGraph = await elk.layout(graph);

        if (cancelled) return;

        // Map back to React Flow format
        const layoutedNodes = layoutedGraph.children?.map((node) => {
          const originalNode = visibleNodes.find(n => n.id === node.id);
          return {
            ...originalNode!,
            position: { x: node.x || 0, y: node.y || 0 },
          };
        }) || [];

        setNodes(layoutedNodes);
        setEdges(visibleEdges);
        setLoading(false);

        // Fit view after a brief delay to allow rendering
        setTimeout(() => {
          window.requestAnimationFrame(() => fitView({ padding: 0.1 }));
        }, 50);
      } catch (err) {
        if (cancelled) return;
        console.error('Layout failed:', err);
        setError(`Layout failed: ${err instanceof Error ? err.message : String(err)}`);
        setLoading(false);
      }
    };

    runLayout();

    return () => {
      cancelled = true;
    };
  }, [visibleNodes, visibleEdges, setNodes, setEdges, fitView]);

  return (
    <Box sx={{ width: '100%', height: 'calc(100vh - 200px)', minHeight: '500px', position: 'relative' }}>
        {loading && (
            <Box sx={{
                position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                backgroundColor: 'rgba(255,255,255,0.8)', zIndex: 10
            }}>
                <CircularProgress />
                <Typography sx={{ ml: 2 }}>Calculating Layout ({visibleNodes.length} visible of {parsedGraph.nodes.length} total)...</Typography>
            </Box>
        )}
        
        {error && (
            <Alert severity="error" sx={{ position: 'absolute', top: 10, left: 10, right: 10, zIndex: 20 }}>
                {error}
            </Alert>
        )}

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        fitView
        onlyRenderVisibleElements={true} // VIRTUALIZATION CRITICAL FOR PERFORMANCE
        minZoom={0.05}
        maxZoom={4}
      >
        <Background color="#aaa" gap={16} />
        <Controls />
        <MiniMap 
            nodeColor={(n: Node) => {
                if (n.type === 'cluster') return '#757575';
                const data = n.data as KnowledgeNodeData;
                const levelColors = ['#1976d2', '#1565c0', '#0d47a1', '#002171'];
                return levelColors[Math.min(data.level || 0, levelColors.length - 1)] || '#1976d2';
            }}
            maskColor="rgb(240, 240, 240, 0.6)"
        />
        <Panel position="top-left">
            <Paper sx={{ p: 2, opacity: 0.95, minWidth: '200px' }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                  Level Controls
                </Typography>
                <Stack spacing={0.5} sx={{ mb: 1 }}>
                  {Array.from({ length: maxLevel + 1 }, (_, i) => {
                    const nodeCount = nodesByLevel.get(i)?.length || 0;
                    return (
                      <Chip
                        key={i}
                        label={`Level ${i} (${nodeCount})`}
                        size="small"
                        color={expandedLevels.has(i) ? 'primary' : 'default'}
                        onClick={() => toggleLevel(i)}
                        sx={{ cursor: 'pointer', justifyContent: 'flex-start' }}
                      />
                    );
                  })}
                </Stack>
                <Stack direction="row" spacing={1}>
                  <Button size="small" variant="outlined" onClick={expandAll} fullWidth>
                    Expand All
                  </Button>
                  <Button size="small" variant="outlined" onClick={collapseAll} fullWidth>
                    Collapse
                  </Button>
                </Stack>
            </Paper>
        </Panel>
        <Panel position="top-right">
            <Paper sx={{ p: 1, opacity: 0.9 }}>
                <Typography variant="caption">
                  Showing: {nodes.length} nodes | {edges.length} edges
                </Typography>
                <Typography variant="caption" display="block">
                  Total: {parsedGraph.nodes.length} nodes
                </Typography>
            </Paper>
        </Panel>
      </ReactFlow>
    </Box>
  );
};

// Wrap with Provider to ensure useReactFlow works
export const KnowledgeSpaceGraph: React.FC<KnowledgeSpaceGraphProps> = (props) => (
  <ReactFlowProvider>
    <GraphInner {...props} />
  </ReactFlowProvider>
);
