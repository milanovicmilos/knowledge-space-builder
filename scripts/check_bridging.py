import pandas as pd
import json
import os

ROOT = os.path.dirname(os.path.dirname(__file__))
CSV = os.path.join(ROOT, 'learning-space-generator', 'data', 'ResponsePatterns_Stellwerk_Math_2018-2024(in).csv')
JSON = os.path.join(ROOT, 'learning_space_28.json')

print('CSV path:', CSV)
print('JSON path:', JSON)

with open(JSON, 'r', encoding='utf-8') as f:
    data = json.load(f)

# build item->cluster map
item2cluster = {}
for c in data.get('clusters', []):
    cid = c['cluster_id']
    for it in c['items']:
        item2cluster[it] = cid

clusters = {}
for it, cid in item2cluster.items():
    clusters.setdefault(cid, []).append(it)

print('Detected clusters:', {k: len(v) for k, v in clusters.items()})

# read only needed columns: student id (first column) and all item columns present in mapping
# determine CSV columns by reading header
with open(CSV, 'r', encoding='utf-8') as f:
    header = f.readline().strip().split(';')

# assume first column is student id or similar; find which item columns exist
available_items = set(header)
mapped_items = [it for it in item2cluster.keys() if it in available_items]
missing = set(item2cluster.keys()) - set(mapped_items)
if missing:
    print('Warning: these items from JSON missing in CSV header (will be ignored):', missing)

usecols = mapped_items.copy()
# include index column if present as first column not in items
idx_col = None
if header[0] not in mapped_items:
    idx_col = header[0]
    usecols = [idx_col] + usecols

print('Reading CSV columns:', len(usecols))

df = pd.read_csv(CSV, sep=';', usecols=usecols, dtype=str)
print('Rows loaded:', len(df))

# treat non-null and non-empty as answered
if idx_col:
    df_index = df[idx_col]
    df_items = df.drop(columns=[idx_col])
else:
    df_index = df.index.astype(str)
    df_items = df

# normalize answers: consider as answered if value not NA/null and not empty and not '0'
def answered_mask(x):
    if pd.isna(x):
        return False
    s = str(x).strip()
    if s == '' or s.lower() in ['na', 'nan']:
        return False
    # treat '0' or 'False' as not answered
    if s in ['0', '0.0', 'false', 'False']:
        return False
    return True

mask = df_items.applymap(answered_mask)

# compute per-student counts per cluster
import numpy as np
cluster_counts = np.zeros((len(mask), len(clusters)), dtype=int)
for cid, items in clusters.items():
    cols = [c for c in items if c in mask.columns]
    if not cols:
        continue
    cluster_counts[:, cid] = mask[cols].sum(axis=1).to_numpy()

# check how many students have >=2 answers in any single cluster
has_multi_in_cluster = (cluster_counts >= 2).any(axis=1)
num_multi = int(has_multi_in_cluster.sum())
total = len(mask)
print('\nStudents with >=2 answers inside any single cluster: {} / {} ({:.4%})'.format(num_multi, total, num_multi/total))

# also check number of students answering at least one item in multiple clusters
answered_any = (cluster_counts >= 1).sum(axis=1)
num_multi_clusters = int((answered_any >= 2).sum())
print('Students with answered items in >=2 different clusters: {} / {} ({:.4%})'.format(num_multi_clusters, total, num_multi_clusters/total))

# sample bridging student indices
bridgers = df_index[has_multi_in_cluster]
print('\nSample of up to 10 student identifiers who answered >=2 items in same cluster:')
print(bridgers.head(10).to_list())

# if num_multi is zero, rule holds strictly for these clusters
if num_multi == 0:
    print('\nResult: No student answered >=2 items within any single cluster (based on given clusters).')
else:
    print('\nResult: Found students who answered multiple items within same cluster.')
