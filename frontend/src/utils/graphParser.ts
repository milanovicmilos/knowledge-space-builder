import type { Node, Edge } from '@xyflow/react';

/**
 * Graph Parser for React Flow
 * Converts knowledge_space.json into React Flow nodes and edges.
 * Optimized for large graphs using ELK layout strategies later.
 */

// Custom data interface for our nodes
export interface KnowledgeNodeData extends Record<string, unknown> {
  label: string;
  fullLabel: string;
  level: number;
  conceptCount: number;
}

export interface ParsedGraph {
  nodes: Node<KnowledgeNodeData>[];
  edges: Edge[];
  levels: Map<number, string[]>;
}

// Shortens concept names for display
function shortenConceptName(name: string): string {
  const replacements: Record<string, string> = {
    'Funktion und Gleichungen': 'F∧G',
    'Lineare Funktionen': 'LF',
    'Anwendungen der Mathematik': 'AM',
    'Finanzmathematik': 'FM',
    'Anwendungsaufgaben / Gleichungen': 'A∧G',
    'Funktionen und Graphen': 'F∧G*',
    'Funktionen': 'Funk.',
    'Funktionalanalyse': 'FA',
    'Geradengleichungen': 'Gle.',
    'Geradengleichungen und Steigungen': 'GLS',
    'Geometrie': 'Geo.',
    'Gleichungen': 'Gl.',
    'Gleichungen und Visualisierungen': 'Gl∧V',
    'Algebra': 'Alg.',
    'Allgemeingültige Gleichungen': 'AllgGl',
    'Analytische Geometrie': 'AnGeo',
    'Differentialrechnung': 'Diff.',
    'Grundlagen der Algebra': 'GdA',
    'Grundlagen der Arithmetik': 'GdAr',
    'Ratenzahlungen und Finanzmathematik': 'RzFM',
    'Steigung': 'Steig.',
  };

  return replacements[name] || name.substring(0, 15) + '...';
}

/**
 * Parses knowledge_space.json into React Flow format.
 * Assigns levels via BFS for layout hinting.
 */
export function parseKnowledgeSpace(
  knowledgeSpace: Record<string, string[]>,
  onProgress?: (current: number, total: number) => void
): ParsedGraph {
  const stateKeys = Object.keys(knowledgeSpace);
  const totalStates = stateKeys.length;
  
  const nodes: Node<KnowledgeNodeData>[] = [];
  const edges: Edge[] = [];
  const levels: Map<number, string[]> = new Map();

  // BFS to determine levels from the root "{}" or empty state
  const visited = new Set<string>();
  // We assume "{}" is the root. If not present, we might need heuristic.
  // Standard knowledge space usually starts with empty set.
  const queue: Array<[string, number]> = [['{}', 0]];
  const nodeLevel: Map<string, number> = new Map();
  let processedCount = 0;

  // We need to handle disconnected components or if '{}' isn't the only root?
  // Ideally, a knowledge space is rooted at empty set.
  // We'll also scan for nodes not reached after main BFS if necessary, 
  // but usually KS is fully reachable from empty set.
  // Just in case, we can iterate all keys to find other roots if queue goes empty and not all visited?
  // For now, let's assume one massive component rooted at {}.
  // If queue is initially empty (no '{}'), just pick the first key?
  if (!knowledgeSpace['{}'] && stateKeys.length > 0) {
     // Fallback: try to find a key with no incoming edges? Too expensive.
     // Just push the first key we found to start traversing.
     if (stateKeys.includes('{}')) {
        // it exists but might be tricky
     } else {
        // weird case, just add the first one
        queue.push([stateKeys[0], 0]);
     }
  }

  // Helper BFS Function
  const runBFS = () => {
    while (queue.length > 0) {
      const [current, level] = queue.shift()!;
  
      if (visited.has(current)) continue;
      visited.add(current);
      nodeLevel.set(current, level);
  
      if (!levels.has(level)) {
        levels.set(level, []);
      }
      levels.get(level)!.push(current);
  
      processedCount++;
      if (onProgress && processedCount % 200 === 0) {
        onProgress(processedCount, totalStates);
      }
  
      const neighbors = knowledgeSpace[current];
      if (neighbors && Array.isArray(neighbors)) {
        for (const next of neighbors) {
          if (!visited.has(next)) {
            queue.push([next, level + 1]);
          }
        }
      }
    }
  };

  runBFS();

  // If we have disconnected parts (not reachable from {}), we should traverse them too
  // to ensure every node gets a node object.
  for (const key of stateKeys) {
      if (!visited.has(key)) {
          queue.push([key, 0]); // Assign level 0 to other roots? Or separate semantic levels?
          runBFS();
      }
  }

  // Create Nodes
  // We iterate visited entries to ensure order logic if needed, or just map the entries.
  // Using nodeLevel map covers all visited nodes.
  for (const [stateKey, level] of nodeLevel.entries()) {
    const concepts = stateKey
      .trim()
      .replace(/^{/, '')
      .replace(/}$/, '')
      .split(',')
      .map((c) => c.trim())
      .filter((c) => c.length > 0);

    const isRoot = stateKey === '{}' || concepts.length === 0;
    const shortLabel = isRoot ? '∅' : concepts.map(shortenConceptName).join(' ');
    const fullLabel = isRoot ? 'Empty Knowledge' : concepts.join(', ');

    // ID Generation: Must be unique and safe for handling
    // btoa is fine, just cleaning special chars
    const nodeId = btoa(stateKey).replace(/[^a-zA-Z0-9]/g, '');

    nodes.push({
      id: nodeId,
      position: { x: 0, y: 0 }, // Initial position, will be set by layout
      data: {
        label: shortLabel,
        fullLabel: fullLabel,
        level: level,
        conceptCount: concepts.length,
      },
      type: 'default', // or custom type
      // Using 'className' for styling if needed
      className: 'knowledge-node',
    });
  }

  // Create Edges
  // Iterate the original knowledgeSpace object
  for (const [source, targets] of Object.entries(knowledgeSpace)) {
    if (!Array.isArray(targets)) continue;
    
    const sourceId = btoa(source).replace(/[^a-zA-Z0-9]/g, '');
    // Only create edges if source node exists (it should)
    // if (!nodeLevel.has(source)) continue; 

    for (const target of targets) {
      const targetId = btoa(target).replace(/[^a-zA-Z0-9]/g, '');
      const edgeId = `e-${sourceId}-${targetId}`;

      edges.push({
        id: edgeId,
        source: sourceId,
        target: targetId,
        // type: 'smoothstep' or 'bezier'
        type: 'smoothstep',
        animated: false,
      });
    }
  }

  return {
    nodes,
    edges,
    levels,
  };
}

/**
 * Extract all unique concepts from the knowledge space keys.
 */
export function extractAllConcepts(knowledgeSpace: Record<string, string[]>): string[] {
  const concepts = new Set<string>();

  for (const stateKey of Object.keys(knowledgeSpace)) {
    const parts = stateKey
      .trim()
      .replace(/^{/, '')
      .replace(/}$/, '')
      .split(',')
      .map((c) => c.trim())
      .filter((c) => c.length > 0);
    parts.forEach((c) => concepts.add(c));
  }

  return Array.from(concepts).sort();
}

/**
 * Find reachable concepts from a given state state (BFS).
 */
export function findReachableConcepts(
  state: string,
  knowledgeSpace: Record<string, string[]>
): string[] {
  const reachable = new Set<string>();
  const queue: string[] = [state];
  const visited = new Set<string>();

  while (queue.length > 0) {
    const current = queue.shift()!;
    if (visited.has(current)) continue;
    visited.add(current);

    const concepts = current
      .trim()
      .replace(/^{/, '')
      .replace(/}$/, '')
      .split(',')
      .map((c) => c.trim())
      .filter((c) => c.length > 0);
    concepts.forEach((c) => reachable.add(c));

    if (knowledgeSpace[current] && Array.isArray(knowledgeSpace[current])) {
      knowledgeSpace[current].forEach((next) => {
        if (!visited.has(next)) {
          queue.push(next);
        }
      });
    }
  }

  return Array.from(reachable).sort();
}
