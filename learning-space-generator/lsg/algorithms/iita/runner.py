"""
IITA Runner

Main execution logic for running IITA (Inductive Item Tree Analysis).
"""

import logging
from typing import List

from .analyzer import IITAAnalyzer

logger = logging.getLogger(__name__)


def run_iita_analysis(response_patterns: List[str],
                     item_names: List[str],
                     min_support: float = 0.01,
                     max_diff: float = 0.05,
                     output_json: str = None,
                     png_output: str = None,
                     verbose: bool = True) -> IITAAnalyzer:
    """
    Pokreni IITA analizu na response patterns.
    
    Args:
        response_patterns: Lista binary stringova
        item_names: Nazivi items
        min_support: Minimum support threshold
        max_diff: Maximum diff threshold za prerequisite odnose
        output_json: Opcioni path za JSON export
        png_output: Opcioni path za PNG graf vizualizaciju
        verbose: Enable logging output
        
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
    
    if verbose:
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
    
    # Visualize prerequisite graph if requested
    if png_output:
        _save_prerequisite_graph(analyzer, png_output)
    
    return analyzer


def _save_prerequisite_graph(analyzer: IITAAnalyzer, png_output: str) -> None:
    """
    Sačuvaj prerequisite graf kao PNG.
    
    Args:
        analyzer: IITAAnalyzer objekat sa prerequisite strukturom
        png_output: Output path za PNG fajl
    """
    try:
        import matplotlib.pyplot as plt
        import networkx as nx
    except ImportError:
        logger.error("❌ matplotlib i networkx su potrebni za vizualizaciju. Instaliraj sa: pip install matplotlib networkx")
        return
    
    # Kreiraj NetworkX graf
    G = nx.DiGraph()
    
    # Dodaj sve items kao nodes
    for item in analyzer.item_names:
        G.add_node(item)
    
    # Dodaj prerequisite edges
    for item, prereqs in analyzer.prerequisites.items():
        for prereq in prereqs:
            G.add_edge(prereq, item)  # prereq -> item (prereq je potreban za item)
    
    # Statistike
    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()
    root_nodes = sum(1 for n, d in G.in_degree() if d == 0)
    leaf_nodes = sum(1 for n, d in G.out_degree() if d == 0)
    
    # Kreiraj figuru
    plt.figure(figsize=(20, 15))
    
    # Layout - spring layout za bolju vizualizaciju
    pos = nx.spring_layout(G, k=1.5, iterations=50, seed=42)
    
    # Node colors based on in-degree (prerequisite level)
    in_degrees = dict(G.in_degree())
    node_colors = [in_degrees.get(node, 0) for node in G.nodes()]
    
    # Draw nodes
    nx.draw_networkx_nodes(G, pos,
                          node_color=node_colors,
                          node_size=300,
                          cmap='YlOrRd',
                          alpha=0.9)
    
    # Draw edges
    nx.draw_networkx_edges(G, pos,
                          edge_color='gray',
                          arrows=True,
                          arrowsize=10,
                          alpha=0.5,
                          width=1.5)
    
    # Labels - prikaži samo root i leaf nodes za čitljivost
    important_nodes = set(
        [n for n, d in G.in_degree() if d == 0] +  # root nodes
        [n for n, d in G.out_degree() if d == 0]   # leaf nodes
    )
    labels = {node: node if node in important_nodes else '' for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=8)
    
    # Title sa statistikama
    plt.title(
        f'IITA Prerequisite Graph\\n'
        f'Items: {n_nodes}, Relations: {n_edges}, '
        f'Root nodes: {root_nodes}, Leaf nodes: {leaf_nodes}',
        fontsize=16, fontweight='bold'
    )
    plt.axis('off')
    plt.tight_layout()
    
    # Sačuvaj
    plt.savefig(png_output, dpi=150, bbox_inches='tight')
    plt.close()
    
    logger.info(f"✓ Prerequisite graph saved to '{png_output}'")
