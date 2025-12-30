import pandas as pd
import numpy as np
import os
from sklearn.metrics import pairwise_distances, silhouette_score
from sklearn.cluster import AgglomerativeClustering

ROOT = os.path.dirname(os.path.dirname(__file__))
CSV = os.path.join(ROOT, 'learning-space-generator', 'data', 'ResponsePatterns_Stellwerk_Math_2018-2024(in).csv')

print('CSV:', CSV)
# read header
with open(CSV, 'r', encoding='utf-8') as f:
    header = f.readline().strip().split(';')

id_col = header[0]
item_cols = header[1:]
print('Items:', len(item_cols))

usecols = [id_col] + item_cols
# read as strings
df = pd.read_csv(CSV, sep=';', usecols=usecols, dtype=str)
print('Rows:', len(df))

# build boolean answer matrix items x students
# treat non-empty/non-0 as answered
def answered_mask(x):
    if pd.isna(x):
        return False
    s = str(x).strip()
    if s == '' or s.lower() in ['na', 'nan']:
        return False
    if s in ['0', '0.0', 'false', 'False']:
        return False
    return True

# apply per column may be faster
mask = df[item_cols].notna() & (df[item_cols].astype(str).applymap(lambda s: str(s).strip()) != '')
# also remove explicit '0' and 'false'
for c in item_cols:
    mask[c] = mask[c] & (~df[c].astype(str).isin(['0','0.0','false','False']))

# convert to numpy array items x students
X = mask.to_numpy(dtype=bool).T  # shape (n_items, n_students)
print('Item matrix shape:', X.shape)

# compute pairwise Jaccard distances between items
print('Computing pairwise Jaccard distances (items)...')
dist = pairwise_distances(X, metric='jaccard')  # items x items

best_k = None
best_score = -1
best_labels = None
scores = {}
K_MIN = 2
K_MAX = min(10, len(item_cols)-1)
print('Testing K from', K_MIN, 'to', K_MAX)
for k in range(K_MIN, K_MAX+1):
    try:
        # scikit-learn changed the parameter name from `affinity` to `metric`.
        # Try affinity first for older versions, fall back to metric for newer ones.
        try:
            clf = AgglomerativeClustering(n_clusters=k, affinity='precomputed', linkage='average')
        except TypeError:
            clf = AgglomerativeClustering(n_clusters=k, metric='precomputed', linkage='average')
        labels = clf.fit_predict(dist)
        sc = silhouette_score(X, labels, metric='jaccard')
        scores[k] = sc
        print('K=',k,'silhouette=',sc)
        if sc > best_score:
            best_score = sc
            best_k = k
            best_labels = labels
    except Exception as e:
        print('K',k,'failed:',e)

print('\nBest K:', best_k, 'score', best_score)
if best_k is None:
    print('Clustering failed; aborting')
    raise SystemExit(1)

# build clusters
clusters = {}
for idx, lab in enumerate(best_labels):
    clusters.setdefault(lab, []).append(item_cols[idx])

print('Cluster sizes:', {k: len(v) for k,v in clusters.items()})

# compute per-cluster student stats
n_students = X.shape[1]
results = []
for cid, cols in clusters.items():
    # indices of items
    idxs = [item_cols.index(c) for c in cols]
    # counts per student
    counts = X[idxs, :].sum(axis=0)
    num_at_least1 = int((counts >= 1).sum())
    num_at_least2 = int((counts >= 2).sum())
    pct1 = num_at_least1 / n_students
    pct2 = num_at_least2 / n_students
    avg_density = counts.sum() / (len(cols) * n_students)
    results.append((cid, len(cols), num_at_least1, pct1, num_at_least2, pct2, avg_density))

# bridging students across clusters
cluster_presence = np.zeros((len(clusters), n_students), dtype=int)
for i, (cid, cols) in enumerate(sorted(clusters.items())):
    idxs = [item_cols.index(c) for c in cols]
    cluster_presence[i,:] = (X[idxs,:].sum(axis=0) >= 1).astype(int)

num_students_in_multi_clusters = int((cluster_presence.sum(axis=0) >= 2).sum())

# print summary
print('\nPer-cluster stats (cluster_id, n_items, students>=1, %>=1, students>=2, %>=2, avg_density)')
for r in sorted(results):
    print(r)
print('\nStudents with answered items in >=2 different inferred clusters:', num_students_in_multi_clusters, '/', n_students, f'({num_students_in_multi_clusters/n_students:.2%})')

# sample bridging students who answered >=2 items in same cluster (for some cluster)
samples = []
for cid, cols in clusters.items():
    idxs = [item_cols.index(c) for c in cols]
    counts = X[idxs,:].sum(axis=0)
    mask_multi = counts >= 2
    idxs_true = np.where(mask_multi)[0]
    if len(idxs_true) > 0:
        # show up to 5 student row ids (from df)
        student_ids = df[id_col].iloc[idxs_true[:5]].tolist()
        samples.append((cid, len(idxs_true), student_ids))

print('\nSample students with >=2 answers inside inferred clusters (up to 5 per cluster):')
for s in samples:
    print('cluster', s[0], 'count', s[1], 'example_ids', s[2])

# Output short recommendation
print('\nRecommendation:')
# if many clusters have non-trivial pct2, clustering is meaningful
meaningful = any(r[5] > 0.01 for r in results)  # >1% students have >=2 answers in cluster
if meaningful:
    print('Data-driven item groups exist: many students answer multiple items inside some inferred groups. Clustering is useful.')
else:
    print('No strong item groups by student co-response. Consider not clustering or merging clusters.')
