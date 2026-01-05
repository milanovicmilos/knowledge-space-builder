import os
import sys
import json
import numpy as np
from collections import Counter

# ensure project root on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from learning_space_generator import lattice

OUT_DIR = 'learning_space_generator/output'
PRED = os.path.join(OUT_DIR, 'pred_probs.npy')
COLS = os.path.join(OUT_DIR, 'item_cols.npy')
THR = 0.6
MIN_SUPPORT = 5

def main():
    probs = np.load(PRED)
    cols = np.load(COLS, allow_pickle=True)
    cols = [str(x) for x in cols]
    binary = probs >= THR

    states = []
    for row in binary:
        s = frozenset([cols[i] for i, v in enumerate(row) if v])
        states.append(s)

    cnt = Counter(states)
    frequent = [s for s, c in cnt.items() if c >= MIN_SUPPORT]
    if frozenset() not in frequent:
        frequent.insert(0, frozenset())

    closed_list = sorted(list(frequent), key=lambda s: (len(s), tuple(sorted(s))))
    poset = lattice.build_poset_from_sets(closed_list)

    out_json = os.path.join(OUT_DIR, 'knowledge_space_empirical.json')
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(poset, f, indent=2, ensure_ascii=False)
    print('Saved', out_json)
    print('States:', len(poset))

if __name__ == '__main__':
    main()
