import json
import networkx as nx
import random
from pypdf import PdfReader
import re

def validate_graph():
    print("Loading implications...")
    try:
        with open('data/implications.json', 'r') as f:
            edges = json.load(f)
    except FileNotFoundError:
        print("Error: data/implications.json not found.")
        return

    # Build Graph
    G = nx.DiGraph()
    edge_list = [(e['source'], e['target']) for e in edges]
    G.add_edges_from(edge_list)
    
    print(f"Graph Analysis: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges.")
    
    # Analyze Components
    components = list(nx.weakly_connected_components(G))
    print(f"Number of weakly connected components: {len(components)}")
    sizes = sorted([len(c) for c in components], reverse=True)
    print(f"Component sizes: {sizes}")
    
    # State Space sizes estimation
    # If 2 components of size A and B. Total states roughly |States(A)| * |States(B)|.
    # A component of size 60 could have 2^60 states if unstructured, or N if linear.
    # The 'explosion' suggests large components with loose structure.
    
    # Validation Phase: Read PDF
    pdf_path = "COINS-alle-Cluster-CH.pdf"
    print(f"\nExtracting text from {pdf_path}...")
    
    try:
        reader = PdfReader(pdf_path)
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return

    print("--- RAW PDF START ---")
    print(full_text[:4000])
    print("--- RAW PDF END ---")

    # Map codes to text
    description_map = {}
    
    found_count = 0
    
    for node in G.nodes():
        # Node format: s1m11a091
        # PDF format: m11a091 (appears to match from char 2 onwards)
        search_term = node[2:] if (node.startswith('s1') or node.startswith('s2')) else node
        
        # Simple find
        idx = full_text.find(search_term)
        if idx != -1:
            # Extract context - take 500 chars after
            snippet = full_text[idx:idx+500].replace('\n', ' ')
            # Clean up multiple spaces
            snippet = " ".join(snippet.split())
            description_map[node] = snippet
            found_count += 1
        else:
            description_map[node] = "Text not found in PDF."
            
    print(f"Found descriptions for {found_count} out of {len(G.nodes())} items.")
    
    # Pick random implications to validate
    print("\n--- Semantic Validation Samples ---")
    
    # Pick 5 random edges
    sample_edges = random.sample(edge_list, min(5, len(edge_list)))
    
    for u, v in sample_edges:
        print(f"\nEdge: {u} -> {v}")
        print(f"  Source ({u}): {description_map.get(u, 'N/A')}")
        print(f"  Target ({v}): {description_map.get(v, 'N/A')}")
        print("  Does it make sense? (Source required for Target?)")

    # Also check if we can explain the 'explosion'
    # Check average degree
    degrees = [d for n, d in G.degree()]
    avg_degree = sum(degrees) / len(degrees)
    print(f"\nAverage Degree: {avg_degree:.2f}")
    
    # Density
    density = nx.density(G)
    print(f"Graph Density: {density:.4f}")

if __name__ == "__main__":
    validate_graph()
