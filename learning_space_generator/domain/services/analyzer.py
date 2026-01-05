import json
import numpy as np
import networkx as nx
from collections import Counter
import logging

logger = logging.getLogger(__name__)


def parse_state_key(key):
    k = key.strip()
    if k == '{}' or k == '{ }':
        return frozenset()
    k = k.strip('{}').strip()
    if not k:
        return frozenset()
    parts = [p.strip() for p in k.split(',') if p.strip()]
    return frozenset(parts)


def load_lattice_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    state_sets = {n: parse_state_key(n) for n in data.keys()}
    return data, state_sets


def analyze_lattice(lattice_json, pred_probs=None, item_cols=None, pred_threshold=0.6):
    mapping, state_sets = load_lattice_json(lattice_json)
    G = nx.DiGraph()
    for u, childs in mapping.items():
        G.add_node(u)
        for v in childs:
            G.add_edge(u, v)

    num_states = len(mapping)
    num_edges = sum(len(v) for v in mapping.values())
    sizes = [len(s) for s in state_sets.values()]
    cnt_sizes = Counter(sizes)
    empty_present = any(len(s) == 0 for s in state_sets.values())
    weak_cc = list(nx.weakly_connected_components(G))
    is_dag = nx.is_directed_acyclic_graph(G)
    longest = None
    if is_dag:
        try:
            longest = nx.algorithms.dag.dag_longest_path_length(G)
        except Exception:
            longest = None

    support_counts = None
    if pred_probs is not None and item_cols is not None:
        probs = np.load(pred_probs)
        cols = np.load(item_cols, allow_pickle=True)
        all_items = sorted({it for s in state_sets.values() for it in s})
        if all_items:
            idx_map = {it: int(np.where(cols == it)[0][0]) for it in all_items}
            binmat = probs[:, [idx_map[it] for it in all_items]] >= pred_threshold
            student_sets = [frozenset([all_items[j] for j, v in enumerate(row) if v]) for row in binmat]
            cnt = Counter(student_sets)
            support_counts = {k: cnt.get(state_sets[k], 0) for k in mapping.keys()}

    summary = dict(
        num_states=num_states,
        num_edges=num_edges,
        size_min=min(sizes) if sizes else 0,
        size_max=max(sizes) if sizes else 0,
        size_mean=float(np.mean(sizes)) if sizes else 0.0,
        size_median=float(np.median(sizes)) if sizes else 0.0,
        counts_by_size=dict(cnt_sizes),
        empty_present=empty_present,
        weak_components=len(weak_cc),
        is_dag=is_dag,
        longest_path=longest,
    )

    if support_counts is not None:
        summary['states_with_support'] = sum(1 for v in support_counts.values() if v > 0)
        summary['total_students_accounted'] = int(sum(support_counts.values()))

    logger.info('Lattice analysis summary: %s', summary)
    return summary
