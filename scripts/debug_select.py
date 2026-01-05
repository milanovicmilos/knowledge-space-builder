import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from learning_space_generator import lattice
import json
import networkx as nx

def main():
    p='learning_space_generator/output/prereq_graph.json'
    with open(p,'r',encoding='utf-8') as f:
        mapping=json.load(f)
    G=nx.DiGraph()
    G.add_nodes_from(mapping.keys())
    for v, preds in mapping.items():
        for u in preds:
            G.add_edge(u,v)
    sel=lattice.select_by_degree(G,30)
    print('selected count:', len(sel))
    print('selected sample:', sel[:40])
    Gsub=G.subgraph(sel).copy()
    roots=[n for n in Gsub.nodes() if Gsub.in_degree(n)==0]
    print('roots in Gsub:', len(roots))
    print('roots sample:', roots[:20])
    # direct test: generate ideals
    states = lattice.generate_learning_space_from_dag(G, items=sel)
    print('generated states count:', len(states))
    ss = list(states)[:10]
    print('sample states:', [sorted(list(s)) for s in ss])

if __name__=='__main__':
    main()
