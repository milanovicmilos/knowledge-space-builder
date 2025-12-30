import os
import pandas as pd
import numpy as np
import networkx as nx

ROOT = os.path.dirname(os.path.dirname(__file__))
CSV = os.path.join(ROOT, 'learning-space-generator', 'data', 'ResponsePatterns_Stellwerk_Math_2018-2024(in).csv')
MAP = os.path.join(ROOT, 'output', 'item_area_partition_greedy.csv')
OUT_DIR = os.path.join(ROOT, 'output')
THRESH = 0.95

# read mapping
map_df = pd.read_csv(MAP)
# ensure columns
if 'item' not in map_df.columns or 'color' not in map_df.columns:
    raise SystemExit('Mapping file must contain item,color')
map_df['color'] = map_df['color'].astype(int)

# load data
with open(CSV, 'r', encoding='utf-8') as f:
    header = f.readline().strip().split(';')
id_col = header[0]
items = header[1:]

df = pd.read_csv(CSV, sep=';', usecols=[id_col]+items, dtype=str)
mask = df[items].notna() & (df[items].astype(str).applymap(lambda s: str(s).strip()) != '')
for c in items:
    mask[c] = mask[c] & (~df[c].astype(str).isin(['0','0.0','false','False']))

n_students = len(df)
print('Students:', n_students)

# build area matrix students x areas
n_areas = map_df['color'].max() + 1
area_items = {a: map_df[map_df['color']==a]['item'].tolist() for a in range(n_areas)}
A = np.zeros((n_students, n_areas), dtype=int)
for a, its in area_items.items():
    cols = [items.index(it) for it in its]
    A[:, a] = (mask.iloc[:, cols].sum(axis=1) >= 1).astype(int)

area_counts = A.sum(axis=0)
area_prev = area_counts / n_students

# pairwise conditional probabilities P(A|B)
edges = []
for a in range(n_areas):
    for b in range(n_areas):
        if a == b:
            continue
        denom = int(area_counts[b])
        if denom == 0:
            continue
        joint = int(((A[:, a] == 1) & (A[:, b] == 1)).sum())
        p = joint / denom
        edges.append((a, b, joint, denom, p))

# create directed graph with weights p
G = nx.DiGraph()
G.add_nodes_from(range(n_areas))
for a,b,joint,denom,p in edges:
    if p >= THRESH:
        G.add_edge(a, b, weight=p, joint=joint, denom=denom)

print('Initial edges >=', THRESH, ':', G.number_of_edges())

# break cycles by removing lowest-weight edges inside SCCs
removed = []
while True:
    try:
        cycles = list(nx.simple_cycles(G))
    except nx.NetworkXNoCycle:
        cycles = []
    if not cycles:
        break
    # find all SCCs with size>1
    sccs = [s for s in nx.strongly_connected_components(G) if len(s) > 1]
    if not sccs:
        break
    for scc in sccs:
        # find edges inside scc
        scc_edges = []
        for u in scc:
            for v in G.successors(u):
                if v in scc:
                    scc_edges.append((u, v, G[u][v]['weight']))
        if not scc_edges:
            continue
        # remove edge with smallest weight
        u,v,w = min(scc_edges, key=lambda x: x[2])
        G.remove_edge(u, v)
        removed.append((u,v,w))

print('Removed', len(removed), 'edges to break cycles')

# topological order
order = list(nx.topological_sort(G))
print('Topological order length:', len(order))

# save edges CSV
edges_out = os.path.join(OUT_DIR, 'area_precedence_edges.csv')
with open(edges_out, 'w', encoding='utf-8') as f:
    f.write('from_area,to_area,joint,count_b,p\n')
    for u,v in G.edges():
        d = G[u][v]
        f.write(f'{u},{v},{d["joint"]},{d["denom"]},{d["weight"]}\n')
print('Saved edges to', edges_out)

# save graphml and dot
nx.write_graphml(G, os.path.join(OUT_DIR, 'area_precedence.graphml'))
nx.drawing.nx_pydot.write_dot(G, os.path.join(OUT_DIR, 'area_precedence.dot'))
print('Saved graph files')

# save order
with open(os.path.join(OUT_DIR, 'area_order.txt'), 'w', encoding='utf-8') as f:
    for a in order:
        f.write(f'{a}\tcount={area_counts[a]}\tprev={area_prev[a]:.5f}\titems={len(area_items[a])}\n')
print('Saved area order to', os.path.join(OUT_DIR, 'area_order.txt'))

# write human-readable rules
with open(os.path.join(OUT_DIR, 'area_precedence_rules.md'), 'w', encoding='utf-8') as f:
    f.write('# Area precedence rules (threshold=' + str(THRESH) + ')\n\n')
    f.write('area_id | #items | #students_with_area | prevalence | implies_areas (p)\n')
    f.write('---|---|---|---|---\n')
    for u in order:
        implies = []
        for v in G.successors(u):
            implies.append(f'{v} (p={G[u][v]["weight"]:.3f}, joint={G[u][v]["joint"]})')
        f.write(f'{u} | {len(area_items[u])} | {area_counts[u]} | {area_prev[u]:.4f} | {"; ".join(implies)}\n')
print('Saved human-readable rules')
