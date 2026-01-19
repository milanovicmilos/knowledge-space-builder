import matplotlib.pyplot as plt
import networkx as nx
import json

def run_visualization():
    print("Loading implications...")
    try:
        with open('data/implications.json', 'r') as f:
            edges = json.load(f)
    except FileNotFoundError:
        print("Error: data/implications.json not found.")
        return

    print("Building Graph...")
    G = nx.DiGraph()
    edge_list = [(e['source'], e['target']) for e in edges]
    G.add_edges_from(edge_list)
    
    # Identify items with no edges (if any need to be added explicitly, load from csv)
    # But usually showing the connected structure is sufficient.
    
    print(f"Graph has {len(G.nodes)} nodes and {len(G.edges)} edges.")
    
    plt.figure(figsize=(12, 12))
    pos = nx.spring_layout(G, k=0.5, iterations=50)
    # Alternatively use graphviz if available for hierarchy
    try:
        from networkx.drawing.nx_agraph import graphviz_layout
        pos = graphviz_layout(G, prog='dot')
    except ImportError:
        pass
        
    nx.draw(G, pos, with_labels=True, node_size=1500, node_color='skyblue', 
            font_size=8, font_weight='bold', arrowsize=15, edge_color='gray')
            
    plt.title("Knowledge Structure (Implication Graph)")
    output_path = 'data/knowledge_structure_graph.png'
    plt.savefig(output_path)
    print(f"Saved visualization to {output_path}")

if __name__ == "__main__":
    run_visualization()
