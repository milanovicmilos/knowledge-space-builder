import pandas as pd
import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
CSV = os.path.join(ROOT, 'learning-space-generator', 'data', 'ResponsePatterns_Stellwerk_Math_2018-2024(in).csv')

prefix_len = int(sys.argv[1]) if len(sys.argv) > 1 else 4
max_examples = int(sys.argv[2]) if len(sys.argv) > 2 else 10

with open(CSV, 'r', encoding='utf-8') as f:
    header = f.readline().strip().split(';')

id_col = header[0]
item_cols = header[1:]

usecols = [id_col] + item_cols

df = pd.read_csv(CSV, sep=';', usecols=usecols, dtype=str)

# prepare mask

def answered_mask(x):
    if pd.isna(x):
        return False
    s = str(x).strip()
    if s == '' or s.lower() in ['na', 'nan']:
        return False
    if s in ['0', '0.0', 'false', 'False']:
        return False
    return True

mask = df[item_cols].applymap(answered_mask)

# build prefix groups
prefix_map = {}
for col in item_cols:
    key = col
    if key.startswith('M') and len(key) > 1:
        core = key[1:]
        p = core[:prefix_len]
    else:
        p = key[:prefix_len]
    prefix_map.setdefault(p, []).append(col)

# find students with >=2 answers in same prefix
examples = []
for idx, row in mask.iterrows():
    for p, cols in prefix_map.items():
        cols_in = [c for c in cols if c in mask.columns]
        if len(cols_in) < 2:
            continue
        cnt = row[cols_in].sum()
        if cnt >= 2:
            answered = [c for c in cols_in if row[c]]
            examples.append((df.at[idx, id_col], p, answered))
            break
    if len(examples) >= max_examples:
        break

print(f'Prefix len = {prefix_len}, found {len(examples)} examples (showing up to {max_examples}):')
for ex in examples:
    sid, p, answered = ex
    print(f'Student {sid} | area {p} | answered items: {answered}')

if not examples:
    print('No examples found for this prefix length.')
