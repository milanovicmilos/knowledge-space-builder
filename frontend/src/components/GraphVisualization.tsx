import { useState, useEffect } from 'react';
import { 
  ReactFlow, 
  MiniMap, 
  Controls, 
  Background,
  BackgroundVariant,
  Panel,
  type Node,
  type Edge
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import './GraphVisualization.css';

interface GraphVisualizationProps {
  graphData: any; // JSON structure from API
  algorithm: 'neat' | 'iita';
}

export function GraphVisualization({ graphData, algorithm }: GraphVisualizationProps) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);

  // NEAT: knowledge states graph
  const convertNEATToFlow = (data: any) => {
    const flowNodes: Node[] = [];
    const flowEdges: Edge[] = [];
    
    let nodeId = 0;
    const stateToId: { [key: string]: string } = {};

    // Create nodes for each knowledge state
    Object.keys(data).forEach((state, index) => {
      const id = `node-${nodeId++}`;
      stateToId[state] = id;
      
      // Position in grid layout
      const level = state.length; // depth based on number of items
      const x = (index % 5) * 200;
      const y = level * 150;

      flowNodes.push({
        id,
        data: { 
          label: state === '∅' ? '∅ (Empty)' : state 
        },
        position: { x, y },
        style: {
          background: state === '∅' ? '#e3f2fd' : '#f3e5f5',
          border: '2px solid',
          borderColor: state === '∅' ? '#1976d2' : '#7b1fa2',
          borderRadius: '12px',
          padding: '10px 20px',
          fontSize: '14px',
          fontWeight: 'bold'
        },
      });
    });

    // Create edges between states
    Object.entries(data).forEach(([source, targets]) => {
      const sourceId = stateToId[source];
      (targets as string[]).forEach((target) => {
        if (stateToId[target]) {
          flowEdges.push({
            id: `${sourceId}-${stateToId[target]}`,
            source: sourceId,
            target: stateToId[target],
            animated: true,
            style: { stroke: '#7b1fa2', strokeWidth: 2 }
          });
        }
      });
    });

    return { nodes: flowNodes, edges: flowEdges };
  };

  // IITA: prerequisite graph
  const convertIITAToFlow = (data: any) => {
    const flowNodes: Node[] = [];
    const flowEdges: Edge[] = [];

    const items = data.items || [];
    const prerequisites = data.prerequisites || {};

    // Create nodes for each item
    items.forEach((item: string, index: number) => {
      const prereqs = prerequisites[item] || [];
      const level = calculateLevel(item, prerequisites);
      
      const x = (index % 8) * 180;
      const y = level * 120;

      flowNodes.push({
        id: item,
        data: { label: item },
        position: { x, y },
        style: {
          background: prereqs.length === 0 ? '#c8e6c9' : '#bbdefb',
          border: '2px solid',
          borderColor: prereqs.length === 0 ? '#388e3c' : '#1976d2',
          borderRadius: '12px',
          padding: '12px 24px',
          fontSize: '13px',
          fontWeight: '600'
        },
      });
    });

    // Create edges for prerequisites
    Object.entries(prerequisites).forEach(([item, prereqs]) => {
      (prereqs as string[]).forEach((prereq) => {
        flowEdges.push({
          id: `${prereq}-${item}`,
          source: prereq,
          target: item,
          animated: true,
          label: 'prerequisite',
          labelStyle: { fontSize: 10, fill: '#666' },
          style: { stroke: '#1976d2', strokeWidth: 2 }
        });
      });
    });

    return { nodes: flowNodes, edges: flowEdges };
  };

  // Calculate depth level for IITA items
  const calculateLevel = (item: string, prerequisites: any): number => {
    const prereqs = prerequisites[item] || [];
    if (prereqs.length === 0) return 0;
    
    return 1 + Math.max(...prereqs.map((p: string) => calculateLevel(p, prerequisites)));
  };

  // Initialize graph when data changes
  useEffect(() => {
    if (!graphData) return;
    
    const { nodes: flowNodes, edges: flowEdges } = algorithm === 'neat' 
      ? convertNEATToFlow(graphData)
      : convertIITAToFlow(graphData);
    
    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [graphData, algorithm]);

  return (
    <div className="graph-visualization">
      <div className="graph-header">
        <h2>📊 {algorithm === 'neat' ? 'Knowledge Space' : 'Prerequisite Relations'}</h2>
        <p className="graph-info">
          {nodes.length} nodes, {edges.length} edges
        </p>
      </div>
      
      <div className="graph-container">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          attributionPosition="bottom-right"
        >
          <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
          <Controls />
          <MiniMap 
            nodeColor={(node) => {
              const style = node.style as any;
              return style?.background || '#e0e0e0';
            }}
            maskColor="rgba(240, 240, 240, 0.6)"
          />
          <Panel position="top-right" className="graph-legend">
            {algorithm === 'neat' ? (
              <div className="legend-content">
                <div className="legend-item">
                  <span className="legend-color" style={{ background: '#e3f2fd', border: '2px solid #1976d2' }}></span>
                  Empty State
                </div>
                <div className="legend-item">
                  <span className="legend-color" style={{ background: '#f3e5f5', border: '2px solid #7b1fa2' }}></span>
                  Knowledge State
                </div>
              </div>
            ) : (
              <div className="legend-content">
                <div className="legend-item">
                  <span className="legend-color" style={{ background: '#c8e6c9', border: '2px solid #388e3c' }}></span>
                  Root Items
                </div>
                <div className="legend-item">
                  <span className="legend-color" style={{ background: '#bbdefb', border: '2px solid #1976d2' }}></span>
                  Dependent Items
                </div>
              </div>
            )}
          </Panel>
        </ReactFlow>
      </div>
    </div>
  );
}
