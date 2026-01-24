import { useState, useCallback, useMemo } from 'react';
import type { Node, Edge } from '@xyflow/react';
import type { ParsedGraph, KnowledgeNodeData } from '../utils/graphParser';
import { MarkerType } from '@xyflow/react';

interface ClusterData extends Record<string, unknown> {
  label: string;
  fullLabel: string;
  level: number;
  conceptCount: number;
  childCount: number;
  clusteredNodeIds: string[];
  isCluster: true;
}

export const useProgressiveGraph = (parsedGraph: ParsedGraph) => {
  const [expandedLevels, setExpandedLevels] = useState(new Set([0, 1, 2]));

  // Group nodes by level
  const nodesByLevel = useMemo(() => {
    const grouped = new Map<number, Node<KnowledgeNodeData>[]>();
    parsedGraph.nodes.forEach(node => {
      const level = node.data.level;
      if (!grouped.has(level)) {
        grouped.set(level, []);
      }
      grouped.get(level)!.push(node);
    });
    return grouped;
  }, [parsedGraph.nodes]);

  const maxLevel = useMemo(() => {
    return Math.max(...Array.from(nodesByLevel.keys()));
  }, [nodesByLevel]);

  // Create cluster nodes for collapsed levels
  const createClusterForLevel = useCallback((level: number): Node<ClusterData> | null => {
    const nodes = nodesByLevel.get(level);
    if (!nodes || nodes.length === 0) return null;

    return {
      id: `cluster-level-${level}`,
      type: 'cluster',
      position: { x: 0, y: 0 },
      data: {
        label: `Level ${level}`,
        fullLabel: `Level ${level} (${nodes.length} nodes)`,
        level: level,
        conceptCount: 0,
        childCount: nodes.length,
        clusteredNodeIds: nodes.map(n => n.id),
        isCluster: true,
      },
    };
  }, [nodesByLevel]);

  // Get visible nodes based on expanded levels
  const visibleNodes = useMemo(() => {
    const nodes: Node[] = [];
    
    for (let level = 0; level <= maxLevel; level++) {
      if (expandedLevels.has(level)) {
        // Show actual nodes for this level
        const levelNodes = nodesByLevel.get(level) || [];
        nodes.push(...levelNodes);
      } else {
        // Show cluster node for this level
        const cluster = createClusterForLevel(level);
        if (cluster) {
          nodes.push(cluster);
        }
      }
    }

    return nodes;
  }, [expandedLevels, nodesByLevel, maxLevel, createClusterForLevel]);

  // Get visible edges based on visible nodes
  const visibleEdges = useMemo(() => {
    const visibleNodeIds = new Set(visibleNodes.map(n => n.id));
    const edges: Edge[] = [];

    parsedGraph.edges.forEach(edge => {
      const sourceVisible = visibleNodeIds.has(edge.source);
      const targetVisible = visibleNodeIds.has(edge.target);

      if (sourceVisible && targetVisible) {
        // Both nodes visible - show normal edge
        edges.push({
          ...edge,
          type: 'smoothstep',
          markerEnd: { type: MarkerType.ArrowClosed },
          style: { stroke: '#b1b1b7', strokeWidth: 1.5 },
        });
      } else {
        // Handle edges to/from clusters
        const sourceNode = parsedGraph.nodes.find(n => n.id === edge.source);
        const targetNode = parsedGraph.nodes.find(n => n.id === edge.target);
        
        if (!sourceNode || !targetNode) return;

        let actualSource = edge.source;
        let actualTarget = edge.target;

        // If target is in collapsed level, point to cluster
        if (!targetVisible && targetNode) {
          const targetLevel = targetNode.data.level;
          if (!expandedLevels.has(targetLevel)) {
            actualTarget = `cluster-level-${targetLevel}`;
          }
        }

        // If source is in collapsed level, start from cluster
        if (!sourceVisible && sourceNode) {
          const sourceLevel = sourceNode.data.level;
          if (!expandedLevels.has(sourceLevel)) {
            actualSource = `cluster-level-${sourceLevel}`;
          }
        }

        // Only add if we have valid cluster connections
        if (visibleNodeIds.has(actualSource) && visibleNodeIds.has(actualTarget)) {
          edges.push({
            id: `${actualSource}-${actualTarget}`,
            source: actualSource,
            target: actualTarget,
            type: 'smoothstep',
            markerEnd: { type: MarkerType.ArrowClosed },
            style: { stroke: '#9e9e9e', strokeWidth: 2, strokeDasharray: '5,5' },
          });
        }
      }
    });

    // Deduplicate edges
    const uniqueEdges = new Map<string, Edge>();
    edges.forEach(edge => {
      const key = `${edge.source}-${edge.target}`;
      if (!uniqueEdges.has(key)) {
        uniqueEdges.set(key, edge);
      }
    });

    return Array.from(uniqueEdges.values());
  }, [visibleNodes, parsedGraph.edges, parsedGraph.nodes, expandedLevels]);

  const expandLevel = useCallback((level: number) => {
    setExpandedLevels(prev => new Set([...prev, level]));
  }, []);

  const collapseLevel = useCallback((level: number) => {
    setExpandedLevels(prev => {
      const next = new Set(prev);
      next.delete(level);
      return next;
    });
  }, []);

  const toggleLevel = useCallback((level: number) => {
    if (expandedLevels.has(level)) {
      collapseLevel(level);
    } else {
      expandLevel(level);
    }
  }, [expandedLevels, expandLevel, collapseLevel]);

  const expandAll = useCallback(() => {
    const allLevels = Array.from(nodesByLevel.keys());
    setExpandedLevels(new Set(allLevels));
  }, [nodesByLevel]);

  const collapseAll = useCallback(() => {
    setExpandedLevels(new Set([0]));
  }, []);

  return {
    visibleNodes,
    visibleEdges,
    expandedLevels,
    maxLevel,
    expandLevel,
    collapseLevel,
    toggleLevel,
    expandAll,
    collapseAll,
    nodesByLevel,
  };
};
