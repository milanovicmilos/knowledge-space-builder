"""
IITA (Inductive Item Tree Analysis) implementacija.

IITA algoritam je dizajniran za otkrivanje prerequisite (surmise) odnosa
između pitanja/items na osnovu response patterns studenata.

Glavne prednosti:
- Radi na velikim domenima (100+ items)
- Brži od NEAT (nema genetski search)
- Daje interpretabilne prerequisite structure (DAG)
- Ne zahteva puno memorije

Reference:
- Schrepp, M. (2003). "A method for the analysis of hierarchical dependencies 
  between items of a questionnaire."
- IITA R package documentation
"""

import numpy as np
import logging
from typing import List, Tuple, Dict, Set
from itertools import combinations
from collections import defaultdict
import json

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

logger = logging.getLogger(__name__)


class IITAAnalyzer:
    """
    IITA (Inductive Item Tree Analysis) za otkrivanje prerequisite struktura.
    
    IITA gradi directed graph gde ivica a -> b znači:
    "Ako student zna b, onda verovatno zna i a" (a je prerequisite za b)
    """
    
    def __init__(self, 
                 response_patterns: List[str],
                 item_names: List[str],
                 min_support: float = 0.01,
                 max_diff: float = 0.05):
        """
        Args:
            response_patterns: Lista binary stringova '0110...' (0=wrong, 1=correct)
            item_names: Nazivi pitanja (npr. ['M178866', 'M183201', ...])
            min_support: Minimum proporcija studenata za validnost odnosa
            max_diff: Maksimalna dozvoljena greška za quasi-order
        """
        self.response_patterns = response_patterns
        self.item_names = item_names
        self.n_items = len(item_names)
        self.n_patterns = len(response_patterns)
        self.min_support = min_support
        self.max_diff = max_diff
        
        # Konvertuj patterns u NumPy array za brzinu
        self.pattern_array = np.array([
            [int(c) for c in pattern] 
            for pattern in response_patterns
        ], dtype=np.uint8)
        
        # Prerequisite graph
        self.prerequisites = {}  # item_a -> set of items that require a
        self.diff_values = {}  # (item_a, item_b) -> diff value
        
    def compute_diff(self, item_a: int, item_b: int) -> float:
        """
        Izračunaj diff vrednost između dva itema.
        
        diff(a, b) = P(a=0 AND b=1) / P(a=0)
        
        Mala diff vrednost znači: "Ako student NE zna a, retko zna b"
        → a je prerequisite za b
        
        Args:
            item_a: Index prvog itema
            item_b: Index drugog itema
            
        Returns:
            diff vrednost [0, 1]
        """
        # Koliko studenata nije znalo a (a=0)
        a_zero = self.pattern_array[:, item_a] == 0
        count_a_zero = np.sum(a_zero)
        
        if count_a_zero == 0:
            return 1.0  # Svi znaju a, nema prerequisite odnosa
        
        # Od onih koji nisu znali a, koliko JE znalo b?
        a_zero_b_one = np.sum((a_zero) & (self.pattern_array[:, item_b] == 1))
        
        diff = a_zero_b_one / count_a_zero
        return diff
    
    def build_prerequisite_structure(self) -> Dict[str, Set[str]]:
        """
        Gradi prerequisite graph koristeći IITA algoritam.
        
        Logika:
        1. Za svaki par (a, b), izračunaj diff(a, b)
        2. Ako diff(a, b) < threshold → a je prerequisite za b
        3. Ukloni transitive odnose (ako a→b i b→c postoje, ukloni a→c)
        
        Returns:
            Dict: {item_name: set of items that require it}
        """
        logger.info(f"\n{'='*80}")
        logger.info("IITA: Building Prerequisite Structure")
        logger.info(f"{'='*80}")
        logger.info(f"Items: {self.n_items}")
        logger.info(f"Patterns: {self.n_patterns:,}")
        logger.info(f"Min support: {self.min_support:.1%}")
        logger.info(f"Max diff threshold: {self.max_diff:.3f}")
        
        # 1. Compute all pairwise diff values
        logger.info("\nComputing pairwise diff values...")
        prerequisite_pairs = []
        
        for i in range(self.n_items):
            for j in range(self.n_items):
                if i == j:
                    continue
                    
                diff = self.compute_diff(i, j)
                self.diff_values[(i, j)] = diff
                
                # Ako diff < threshold, i je prerequisite za j
                if diff < self.max_diff:
                    prerequisite_pairs.append((i, j, diff))
        
        logger.info(f"Found {len(prerequisite_pairs)} potential prerequisite relations")
        
        # 2. Build adjacency structure
        adj_list = defaultdict(set)
        for item_a, item_b, diff in prerequisite_pairs:
            adj_list[item_a].add(item_b)
        
        # 3. Transitive reduction - ukloni redundantne ivice
        logger.info("\nPerforming transitive reduction...")
        if NETWORKX_AVAILABLE:
            # Koristi NetworkX - testirana implementacija
            G = nx.DiGraph()
            for node, successors in adj_list.items():
                for successor in successors:
                    G.add_edge(node, successor)
            
            logger.info(f"  Original graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
            
            # Check for cycles - transitive_reduction zahteva DAG!
            if not nx.is_directed_acyclic_graph(G):
                logger.warning(f"  Graph contains cycles - removing them first...")
                
                # Ukloni cikluse zadržavajući što više ivica
                # Strategija: ukloni ivice sa NAJVEĆIM diff vrednostima (najslabije veze)
                cycles_removed = 0
                while not nx.is_directed_acyclic_graph(G):
                    try:
                        # Nađi jedan ciklus
                        cycle = nx.find_cycle(G, orientation='original')
                        
                        # Nađi ivicu u ciklusu sa NAJVEĆIM diff (najslabija veza)
                        worst_edge = None
                        worst_diff = -1
                        
                        for u, v, direction in cycle:
                            # Nađi diff vrednost za ovu ivicu
                            diff_val = self.diff_values.get((u, v), 1.0)
                            if diff_val > worst_diff:
                                worst_diff = diff_val
                                worst_edge = (u, v)
                        
                        # Ukloni najslabiju ivicu
                        if worst_edge:
                            G.remove_edge(*worst_edge)
                            cycles_removed += 1
                    except nx.NetworkXNoCycle:
                        break
                
                logger.info(f"  Removed {cycles_removed} edges to break cycles")
                logger.info(f"  DAG graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
            
            # Transitive reduction
            G_reduced = nx.transitive_reduction(G)
            
            logger.info(f"  Reduced graph: {G_reduced.number_of_nodes()} nodes, {G_reduced.number_of_edges()} edges")
            logger.info(f"  Removed {G.number_of_edges() - G_reduced.number_of_edges()} redundant edges")
            
            # Convert back to adjacency list
            adj_list = defaultdict(set)
            for u, v in G_reduced.edges():
                adj_list[u].add(v)
        else:
            logger.warning("  NetworkX not available - skipping transitive reduction")
        
        # 4. Convert to named items
        self.prerequisites = {
            self.item_names[item_idx]: {
                self.item_names[succ] for succ in successors
            }
            for item_idx, successors in adj_list.items()
        }
        
        # Statistics
        total_edges = sum(len(s) for s in self.prerequisites.values())
        logger.info(f"\n{'='*80}")
        logger.info("IITA Results:")
        logger.info(f"  Total prerequisite relations: {total_edges}")
        logger.info(f"  Items with prerequisites: {len([k for k, v in self.prerequisites.items() if v])}")
        logger.info(f"  Root items (no prerequisites): {self.n_items - len(self.prerequisites)}")
        logger.info(f"{'='*80}\n")
        
        return self.prerequisites
    
    def _transitive_reduction(self, adj_list: Dict[int, Set[int]]) -> Dict[int, Set[int]]:
        """
        Ukloni transitive edges iz grafa.
        
        Ako postoji a→b→c, ukloni direktnu ivicu a→c.
        """
        reduced = {}
        
        for node in adj_list:
            # Za svaki node, nađi sve reachable nodes
            reachable = self._get_reachable(node, adj_list, exclude_direct=True)
            
            # Direct successors minus transitive ones
            direct = adj_list[node]
            reduced[node] = direct - reachable
        
        return reduced
    
    def _get_reachable(self, 
                      start: int, 
                      adj_list: Dict[int, Set[int]], 
                      exclude_direct: bool = False) -> Set[int]:
        """
        Nađi sve reachable nodes iz start node (DFS).
        
        Args:
            start: Početni node
            adj_list: Adjacency list
            exclude_direct: Ako True, ne uključuj direktne successore
            
        Returns:
            Set svih reachable nodes
        """
        visited = set()
        stack = []
        
        # Inicijalizuj stack sa direct successors
        if start in adj_list:
            if exclude_direct:
                # Kreni od successora successora
                for successor in adj_list[start]:
                    if successor in adj_list:
                        stack.extend(adj_list[successor])
            else:
                stack.extend(adj_list[start])
        
        # DFS
        while stack:
            node = stack.pop()
            if node not in visited:
                visited.add(node)
                if node in adj_list:
                    stack.extend(adj_list[node])
        
        return visited
    
    def to_json(self, filepath: str = None) -> str:
        """
        Eksportuj prerequisite strukturu u JSON format.
        
        Format:
        {
            "items": [...],
            "prerequisites": {
                "item_a": ["item_x", "item_y"],  // a je prerequisite za x i y
                ...
            },
            "metadata": {...}
        }
        """
        data = {
            "items": self.item_names,
            "prerequisites": {
                item: list(successors) 
                for item, successors in self.prerequisites.items()
                if successors  # Samo items sa prerequisite vezama
            },
            "metadata": {
                "n_items": self.n_items,
                "n_patterns": self.n_patterns,
                "min_support": self.min_support,
                "max_diff": self.max_diff,
                "total_relations": sum(len(s) for s in self.prerequisites.values())
            }
        }
        
        json_str = json.dumps(data, indent=2)
        
        if filepath:
            with open(filepath, 'w') as f:
                f.write(json_str)
            logger.info(f"Prerequisite structure saved to: {filepath}")
        
        return json_str
    
    def get_item_difficulty(self) -> Dict[str, float]:
        """
        Izračunaj difficulty (P-value) za svaki item.
        
        P-value = procenat studenata koji su tačno odgovorili.
        
        Returns:
            Dict: {item_name: difficulty_score}
        """
        difficulties = {}
        for i, item_name in enumerate(self.item_names):
            p_value = np.mean(self.pattern_array[:, i])
            difficulties[item_name] = float(p_value)
        
        return difficulties
    
    def get_prerequisite_chains(self, max_chains: int = 100, max_depth: int = 10) -> List[List[str]]:
        """
        Nađi sve prerequisite chains (paths) u grafu.
        
        Chain: A → B → C → D (A je prerequisite za B, B za C, itd.)
        
        Args:
            max_chains: Maximum broj chains da vrati (prevent explosion)
            max_depth: Maximum dubina chain-a
        
        Returns:
            Lista lanaca, svaki lanac je lista item names
        """
        chains = []
        
        # Nađi root nodes (items bez prerequisites)
        all_items = set(self.item_names)
        items_with_prereqs = set()
        for successors in self.prerequisites.values():
            items_with_prereqs.update(successors)
        
        root_items = all_items - items_with_prereqs
        
        # DFS od svakog root node-a
        for root in root_items:
            if len(chains) >= max_chains:
                break
            if root in self.prerequisites and self.prerequisites[root]:
                self._find_chains_from(root, [root], chains, max_chains, max_depth)
        
        return chains
    
    def _find_chains_from(self, 
                         current: str, 
                         path: List[str], 
                         chains: List[List[str]],
                         max_chains: int = 100,
                         max_depth: int = 10):
        """Rekurzivno nađi sve chains od current item."""
        # Safety limits
        if len(chains) >= max_chains:
            return
        if len(path) >= max_depth:
            # Previše dubok - dodaj kao chain i završi
            if len(path) > 1:
                chains.append(path.copy())
            return
        
        if current not in self.prerequisites or not self.prerequisites[current]:
            # Leaf node - dodaj chain
            if len(path) > 1:  # Samo chains sa bar 2 itema
                chains.append(path.copy())
            return
        
        for successor in self.prerequisites[current]:
            if successor not in path:  # Izbegni cikluse
                path.append(successor)
                self._find_chains_from(successor, path, chains, max_chains, max_depth)
                path.pop()
            
            # Early exit ako smo dostigli limit
            if len(chains) >= max_chains:
                return


def run_iita_analysis(response_patterns: List[str],
                     item_names: List[str],
                     min_support: float = 0.01,
                     max_diff: float = 0.05,
                     output_json: str = None) -> IITAAnalyzer:
    """
    Pokreni IITA analizu na response patterns.
    
    Args:
        response_patterns: Lista binary stringova
        item_names: Nazivi items
        min_support: Minimum support threshold
        max_diff: Maximum diff threshold za prerequisite odnose
        output_json: Opcioni path za JSON export
        
    Returns:
        IITAAnalyzer objekat sa prerequisite strukturom
    """
    analyzer = IITAAnalyzer(
        response_patterns=response_patterns,
        item_names=item_names,
        min_support=min_support,
        max_diff=max_diff
    )
    
    # Gradi prerequisite strukturu
    analyzer.build_prerequisite_structure()
    
    # Compute item difficulties
    difficulties = analyzer.get_item_difficulty()
    
    logger.info("\nItem Difficulties (top 10 easiest):")
    sorted_items = sorted(difficulties.items(), key=lambda x: x[1], reverse=True)
    for item, diff in sorted_items[:10]:
        logger.info(f"  {item}: {diff:.1%} correct")
    
    # Find prerequisite chains
    chains = analyzer.get_prerequisite_chains()
    if chains:
        logger.info(f"\nFound {len(chains)} prerequisite chains")
        logger.info("Top 5 longest chains:")
        chains.sort(key=len, reverse=True)
        for chain in chains[:5]:
            logger.info(f"  {' → '.join(chain)}")
    
    # Export
    if output_json:
        analyzer.to_json(output_json)
    
    return analyzer
