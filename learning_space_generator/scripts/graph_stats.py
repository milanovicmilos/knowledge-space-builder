"""Graph Statistics Analysis"""
import json
import networkx as nx
from pathlib import Path

output_dir = Path("output")
implications = json.load(open(output_dir / "implications.json"))

G = nx.DiGraph()
G.add_edges_from([(e['source'], e['target']) for e in implications])

print("=" * 80)
print("GRAPH STATISTICS")
print("=" * 80)
print(f"  Nodes (Concepts): {G.number_of_nodes()}")
print(f"  Edges (Prerequisites): {G.number_of_edges()}")
print(f"  Density: {nx.density(G):.4f}")
print(f"  Is DAG: {nx.is_directed_acyclic_graph(G)}")
print(f"  Weakly connected: {nx.is_weakly_connected(G)}")

if nx.is_directed_acyclic_graph(G):
    longest = nx.dag_longest_path(G)
    print(f"  Longest prerequisite chain: {len(longest)} concepts")
    print(f"  Path: {' → '.join(longest)}")

# In-degree and out-degree analysis
in_degrees = dict(G.in_degree())
out_degrees = dict(G.out_degree())

print(f"\n  Root concepts (in-degree=0): {len([n for n in G.nodes() if in_degrees[n] == 0])}")
print(f"  Terminal concepts (out-degree=0): {len([n for n in G.nodes() if out_degrees[n] == 0])}")

print("\n  Top 5 concepts by prerequisites (in-degree):")
for node, degree in sorted(in_degrees.items(), key=lambda x: x[1], reverse=True)[:5]:
    print(f"    {node}: {degree} prerequisites")

print("\n  Top 5 concepts that are prerequisites for others (out-degree):")
for node, degree in sorted(out_degrees.items(), key=lambda x: x[1], reverse=True)[:5]:
    print(f"    {node}: enables {degree} other concepts")
