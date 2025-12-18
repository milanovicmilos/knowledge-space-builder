"""
Vizualizuj IITA prerequisite graf iz JSON fajla.
"""

import json
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import networkx as nx

def load_iita_json(filepath):
    """Učitaj IITA JSON."""
    with open(filepath, 'r') as f:
        return json.load(f)

def create_graph_from_iita(data):
    """Kreiraj NetworkX graf iz IITA podataka."""
    G = nx.DiGraph()
    
    # Dodaj sve items kao nodes
    for item in data['items']:
        G.add_node(item)
    
    # Dodaj prerequisite edges
    for item, successors in data['prerequisites'].items():
        for successor in successors:
            G.add_edge(item, successor)
    
    return G

def visualize_graph(G, title, output_path):
    """Vizualizuj graf."""
    plt.figure(figsize=(20, 15))
    
    # Layout - use spring layout for all
    pos = nx.spring_layout(G, k=1.5, iterations=50, seed=42)
    
    # Node colors based on in-degree (prerequisite level)
    in_degrees = dict(G.in_degree())
    node_colors = [in_degrees.get(node, 0) for node in G.nodes()]
    
    # Draw
    nx.draw_networkx_nodes(G, pos, 
                          node_color=node_colors,
                          node_size=300,
                          cmap='YlOrRd',
                          alpha=0.9)
    
    nx.draw_networkx_edges(G, pos,
                          edge_color='gray',
                          arrows=True,
                          arrowsize=10,
                          alpha=0.5,
                          width=1.5)
    
    # Labels - prikaži samo root nodes i leaf nodes za čitljivost
    root_nodes = [n for n, d in G.in_degree() if d == 0]
    leaf_nodes = [n for n, d in G.out_degree() if d == 0]
    important_nodes = set(root_nodes + leaf_nodes)
    
    labels = {node: node if node in important_nodes else '' for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=8)
    
    plt.title(title, fontsize=16, fontweight='bold')
    plt.axis('off')
    plt.tight_layout()
    
    # Sačuvaj
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"✓ Graf sačuvan: {output_path}")
    
    return pos

def compare_graphs(json1_path, json2_path, output_dir):
    """Uporedi dva IITA grafa."""
    data1 = load_iita_json(json1_path)
    data2 = load_iita_json(json2_path)
    
    G1 = create_graph_from_iita(data1)
    G2 = create_graph_from_iita(data2)
    
    # Statistics
    print("\n" + "="*80)
    print("POREĐENJE GRAFOVA")
    print("="*80)
    
    print(f"\nGraf 1: {Path(json1_path).name}")
    print(f"  Items: {G1.number_of_nodes()}")
    print(f"  Relations: {G1.number_of_edges()}")
    print(f"  Root nodes: {sum(1 for n, d in G1.in_degree() if d == 0)}")
    print(f"  Leaf nodes: {sum(1 for n, d in G1.out_degree() if d == 0)}")
    print(f"  Avg in-degree: {sum(d for n, d in G1.in_degree()) / G1.number_of_nodes():.2f}")
    print(f"  Max path length: {nx.dag_longest_path_length(G1) if nx.is_directed_acyclic_graph(G1) else 'N/A (cyclic)'}")
    
    print(f"\nGraf 2: {Path(json2_path).name}")
    print(f"  Items: {G2.number_of_nodes()}")
    print(f"  Relations: {G2.number_of_edges()}")
    print(f"  Root nodes: {sum(1 for n, d in G2.in_degree() if d == 0)}")
    print(f"  Leaf nodes: {sum(1 for n, d in G2.out_degree() if d == 0)}")
    print(f"  Avg in-degree: {sum(d for n, d in G2.in_degree()) / G2.number_of_nodes():.2f}")
    print(f"  Max path length: {nx.dag_longest_path_length(G2) if nx.is_directed_acyclic_graph(G2) else 'N/A (cyclic)'}")
    
    print("="*80 + "\n")
    
    # Vizualizuj oba grafa
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    visualize_graph(G1, 
                   f"IITA Graph: {Path(json1_path).stem}\n{G1.number_of_edges()} relations, {sum(1 for n, d in G1.in_degree() if d == 0)} roots",
                   output_dir / f"{Path(json1_path).stem}.png")
    
    visualize_graph(G2,
                   f"IITA Graph: {Path(json2_path).stem}\n{G2.number_of_edges()} relations, {sum(1 for n, d in G2.in_degree() if d == 0)} roots",
                   output_dir / f"{Path(json2_path).stem}.png")
    
    # Side-by-side comparison
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(24, 12))
    
    # Graph 1
    plt.sca(ax1)
    pos1 = nx.spring_layout(G1, k=1, iterations=30, seed=42)
    nx.draw(G1, pos1, node_size=100, node_color='lightblue', 
            edge_color='gray', arrows=True, arrowsize=5, alpha=0.7, ax=ax1)
    ax1.set_title(f"{Path(json1_path).stem}\n{G1.number_of_edges()} edges, {sum(1 for n, d in G1.in_degree() if d == 0)} roots", 
                  fontsize=14, fontweight='bold')
    ax1.axis('off')
    
    # Graph 2
    plt.sca(ax2)
    pos2 = nx.spring_layout(G2, k=1, iterations=30, seed=42)
    nx.draw(G2, pos2, node_size=100, node_color='lightcoral',
            edge_color='gray', arrows=True, arrowsize=5, alpha=0.7, ax=ax2)
    ax2.set_title(f"{Path(json2_path).stem}\n{G2.number_of_edges()} edges, {sum(1 for n, d in G2.in_degree() if d == 0)} roots",
                  fontsize=14, fontweight='bold')
    ax2.axis('off')
    
    plt.tight_layout()
    comparison_path = output_dir / "comparison.png"
    plt.savefig(comparison_path, dpi=150, bbox_inches='tight')
    print(f"✓ Poređenje sačuvano: {comparison_path}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python visualize_iita.py <json1> <json2> [output_dir]")
        sys.exit(1)
    
    json1_path = sys.argv[1]
    json2_path = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "output/visualizations"
    
    compare_graphs(json1_path, json2_path, output_dir)
