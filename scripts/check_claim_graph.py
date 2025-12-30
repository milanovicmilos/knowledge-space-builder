import os
import pandas as pd
import numpy as np
import networkx as nx

ROOT = os.path.dirname(os.path.dirname(__file__))
CSV = os.path.join(ROOT, 'learning-space-generator', 'data', 'ResponsePatterns_Stellwerk_Math_2018-2024(in).csv')
with open(CSV, 'r', encoding='utf-8') as f:
    header = f.readline().strip().split(';')
id_col = header[0]
items = header[1:]
print('Items:', len(items))

# read whole CSV
df = pd.read_csv(CSV, sep=';', usecols=[id_col]+items, dtype=str)
# build answered mask
mask = df[items].notna() & (df[items].astype(str).applymap(lambda s: str(s).strip()) != '')
for c in items:
    mask[c] = mask[c] & (~df[c].astype(str).isin(['0','0.0','false','False']))

n_students = len(df)
print('Students:', n_students)

# co-occurrence counts
print('Computing co-occurrence matrix...')
M = mask.astype(int).to_numpy()  # students x items
co = M.T.dot(M)  # items x items counts

# build graph: edge between i,j if co[i,j] > 0 and i != j
G = nx.Graph()
G.add_nodes_from(items)
for i in range(len(items)):
    for j in range(i+1, len(items)):
        if co[i,j] > 0:
            G.add_edge(items[i], items[j], weight=int(co[i,j]))

print('Graph: nodes', G.number_of_nodes(), 'edges', G.number_of_edges())

# maximum clique (exact) - feasible for 120 nodes
print('Searching for maximal cliques (this may take a moment)...')
max_clique_size = 0
max_cliques = []
for clique in nx.find_cliques(G):
    s = len(clique)
    if s > max_clique_size:
        max_clique_size = s
        max_cliques = [clique]
    elif s == max_clique_size:
        max_cliques.append(clique)

print('Max clique size:', max_clique_size)
if max_clique_size <= 10:
    print('Example max cliques (up to 5):')
    for c in max_cliques[:5]:
        print(c)
else:
    print('Large max clique; showing first example:')
    print(max_cliques[0])

# greedy coloring upper bound
print('Computing greedy coloring (largest_first)...')
coloring = nx.coloring.greedy_color(G, strategy='largest_first')
num_colors = max(coloring.values()) + 1
print('Greedy coloring used', num_colors, 'colors')

# report nodes per color
from collections import defaultdict
colors = defaultdict(list)
for node, col in coloring.items():
    colors[col].append(node)
print('Color sizes:', {c: len(v) for c,v in colors.items()})

# Additional check: are there students who answered >=2 items? (trivial)
counts_per_student = M.sum(axis=1)
num_multi = int((counts_per_student >= 2).sum())
print('Students who answered >=2 items:', num_multi, '/', n_students, f'({num_multi/n_students:.2%})')

# Save counterexample student IDs for any chosen area partitioning: if using greedy coloring with K colors,
# find students that have >=2 items assigned to same color (violators if professor claims K areas).
out_rows = []
for idx in range(n_students):
    # map student's answered items to colors
    answered_idxs = np.where(M[idx,:] == 1)[0]
    if len(answered_idxs) <= 1:
        continue
    cols = [coloring[items[i]] for i in answered_idxs]
    # check duplicates
    if len(set(cols)) < len(cols):
        out_rows.append((df[id_col].iat[idx], answered_idxs.tolist(), cols))

print('Violators w.r.t greedy coloring (students with >=2 answered items in same color):', len(out_rows))
# save a small CSV of violators
out_path = os.path.join(ROOT, 'output', 'area_claim_violators_greedy.csv')
if not os.path.isdir(os.path.dirname(out_path)):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, 'w', encoding='utf-8') as f:
    f.write('student_id,answered_item_indices,colors\n')
    for sid, idxs, cols in out_rows:
        f.write(f'"{sid}","{idxs}","{cols}"\n')
print('Saved violators to', out_path)

# save item -> color mapping
map_path = os.path.join(ROOT, 'output', 'item_area_partition_greedy.csv')
with open(map_path, 'w', encoding='utf-8') as f:
    f.write('item,color\n')
    for item in items:
        f.write(f'"{item}",{coloring[item]}\n')
print('Saved item->area mapping to', map_path)

# Final conclusion message
print('\nConclusion help:')
print('- A partition of items where no student ever answers >1 item per area exists iff the co-occurrence graph is k-colorable with k equal to chosen number of areas.')
print(f'- Lower bound (clique size) = {max_clique_size}; any valid partition requires at least this many areas.')
print(f'- Greedy upper bound = {num_colors}; so it is possible with at most {num_colors} areas.')
print('- If professor implies a small number of areas (<< greddy upper bound), claim is unlikely. If he allows as many areas as items, trivially possible.')
