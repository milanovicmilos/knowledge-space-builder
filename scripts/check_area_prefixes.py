import pandas as pd
import os

ROOT = os.path.dirname(os.path.dirname(__file__))
CSV = os.path.join(ROOT, 'learning-space-generator', 'data', 'ResponsePatterns_Stellwerk_Math_2018-2024(in).csv')

print('CSV:', CSV)

# read header only to get columns
with open(CSV, 'r', encoding='utf-8') as f:
    header = f.readline().strip().split(';')

# assume first column is student id (not an item)
item_cols = header[1:]
print('Detected item columns:', len(item_cols))

# read only columns: id + items
usecols = [header[0]] + item_cols

df = pd.read_csv(CSV, sep=';', usecols=usecols, dtype=str)
print('Rows:', len(df))

id_col = header[0]
df_index = df[id_col]
df_items = df.drop(columns=[id_col])

# answered mask
def answered_mask(x):
    if pd.isna(x):
        return False
    s = str(x).strip()
    if s == '' or s.lower() in ['na', 'nan']:
        return False
    if s in ['0', '0.0', 'false', 'False']:
        return False
    return True

mask = df_items.applymap(answered_mask)

results = []
for prefix_len in range(1, 7):
    # compute prefix keys for each item
    prefixes = {}
    for col in item_cols:
        key = col
        if key.startswith('M') and len(key) > 1:
            core = key[1:]
            p = core[:prefix_len]
        else:
            p = key[:prefix_len]
        prefixes.setdefault(p, []).append(col)
    # for each student compute whether they answered >=2 items within any prefix group
    import numpy as np
    n = len(mask)
    any_multi = np.zeros(n, dtype=bool)
    # also count how many prefixes each student has at least one answer in
    multi_prefix_count = np.zeros(n, dtype=int)
    for p, cols in prefixes.items():
        cols_in = [c for c in cols if c in mask.columns]
        if not cols_in:
            continue
        counts = mask[cols_in].sum(axis=1).to_numpy()
        any_multi |= (counts >= 2)
        multi_prefix_count += (counts >= 1).astype(int)
    num_multi = int(any_multi.sum())
    num_multi_prefixes = int((multi_prefix_count >= 2).sum())
    results.append((prefix_len, len(prefixes), num_multi, num_multi/ n, num_multi_prefixes, num_multi_prefixes / n))

print('\nPrefixLen | #Areas | students>=2-in-area | % | students in >=2 areas | %')
for r in results:
    print('{:9d} | {:6d} | {:18d} | {:5.2%} | {:18d} | {:5.2%}'.format(*r))

# determine if any prefix_len yields zero students with >=2 answers in same area
zero_found = [r for r in results if r[2] == 0]
if zero_found:
    print('\nThere exists at least one prefix length where no student answered >=2 items within same area:')
    for z in zero_found:
        print(' prefix_len', z[0], 'areas', z[1])
else:
    print('\nNo prefix length (1..6) produced zero students with >=2 answers in same area; professor\'s claim is NOT supported by these heuristics.')
