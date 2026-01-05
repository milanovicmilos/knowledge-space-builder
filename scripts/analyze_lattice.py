#!/usr/bin/env python3
"""Analyze a knowledge-space lattice JSON and predicted probabilities.

Usage:
  python scripts/analyze_lattice.py --lattice PATH --pred_probs PATH --item_cols PATH --pred_threshold 0.6 --out_prefix PREFIX
"""
import argparse
import json
import numpy as np
import networkx as nx
from collections import Counter
import math
import os


def parse_state_str(s):
    # input like '{M1, M2, M3}' or '{}'
    s = s.strip()
    if s == '{}' or s == '':
        return frozenset()
    if s.startswith('{') and s.endswith('}'):
        inner = s[1:-1].strip()
        if not inner:
            return frozenset()
        items = [x.strip() for x in inner.split(',')]
        return frozenset(items)
    # fallback
    parts = [p.strip() for p in s.split(',') if p.strip()]
    return frozenset(parts)


def longest_path_length_dag(G):
    # G is a DAG (directed). Return length in nodes of the longest path.
    if not nx.is_directed_acyclic_graph(G):
        return None
    topo = list(nx.topological_sort(G))
    dist = {n: 1 for n in topo}  # path length in nodes
    for u in topo:
        for v in G.successors(u):
            dist[v] = max(dist.get(v, 1), dist[u] + 1)
    return max(dist.values()) if dist else 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--lattice', required=True)
    p.add_argument('--pred_probs', required=True)
    p.add_argument('--item_cols', required=True)
    p.add_argument('--pred_threshold', type=float, default=0.6)
    p.add_argument('--out_prefix', required=True)
    args = p.parse_args()

    with open(args.lattice, 'r', encoding='utf-8') as f:
        lattice = json.load(f)

    # nodes are keys of JSON; values are lists of child state strings
    nodes = list(lattice.keys())
    num_states = len(nodes)
    num_edges = sum(len(v) for v in lattice.values())

    # parse sizes
    sizes = [len(parse_state_str(s)) for s in nodes]
    size_stats = {
        'min': int(min(sizes)) if sizes else 0,
        'max': int(max(sizes)) if sizes else 0,
        'mean': float(np.mean(sizes)) if sizes else 0.0,
        'median': float(np.median(sizes)) if sizes else 0.0,
    }
    size_counts = Counter(sizes)
    top_sizes = size_counts.most_common(10)

    empty_present = any(s.strip() == '{}' for s in nodes)

    # build directed graph
    G = nx.DiGraph()
    G.add_nodes_from(nodes)
    for u, children in lattice.items():
        for v in children:
            G.add_edge(u, v)

    weak_cc = nx.number_weakly_connected_components(G)
    is_dag = nx.is_directed_acyclic_graph(G)
    longest = longest_path_length_dag(G) if is_dag else None

    # levels: compute longest distance from empty set node if present, else from sources
    levels = {}
    if empty_present:
        root = '{}'
        # BFS for level by shortest path length (edges)
        dist = {n: math.inf for n in G.nodes}
        from collections import deque
        dq = deque()
        dist[root] = 0
        dq.append(root)
        while dq:
            u = dq.popleft()
            for v in G.successors(u):
                if dist[v] > dist[u] + 1:
                    dist[v] = dist[u] + 1
                    dq.append(v)
        # compact first 10 levels
        for k, cnt in Counter([d for d in dist.values() if d < math.inf]).items():
            levels[int(k)] = int(cnt)
    else:
        # use in-degree 0 nodes as roots
        roots = [n for n in G.nodes if G.in_degree(n) == 0]
        levels = {'roots': len(roots)}

    # load preds and items
    preds = np.load(args.pred_probs)
    item_cols = np.load(args.item_cols, allow_pickle=True)
    # ensure 1D string array
    item_cols = [str(x) for x in item_cols]

    # binarize rows
    binarized = preds >= args.pred_threshold

    # create mapping from frozenset of item ids to count of exact matches
    state_sets = {parse_state_str(s): s for s in nodes}
    support_counts = {s: 0 for s in nodes}

    # build student sets lazily and count
    for i in range(binarized.shape[0]):
        row = binarized[i]
        student_items = frozenset([item_cols[j] for j, val in enumerate(row) if val])
        if student_items in state_sets:
            sstr = state_sets[student_items]
            support_counts[sstr] += 1

    states_with_support = sum(1 for c in support_counts.values() if c > 0)
    total_students_mapped = sum(support_counts.values())

    summary = {
        'lattice_file': os.path.abspath(args.lattice),
        'num_states': int(num_states),
        'num_edges': int(num_edges),
        'size_stats': size_stats,
        'top_size_counts': top_sizes,
        'empty_present': bool(empty_present),
        'weakly_connected_components': int(weak_cc),
        'is_dag': bool(is_dag),
        'longest_chain_nodes': int(longest) if longest is not None else None,
        'levels_sample': {int(k): v for k, v in list(levels.items())[:10]},
        'states_with_support': int(states_with_support),
        'total_students_mapped': int(total_students_mapped),
        'pred_threshold': float(args.pred_threshold),
    }

    out_json = args.out_prefix + '.json'
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    # print concise
    print('Datoteka:', os.path.basename(args.lattice))
    print('Broj stanja:', summary['num_states'])
    print('Broj Hasse-ivica (cover relations):', summary['num_edges'])
    print('Veličine stanja: min=%d, max=%d, mean≈%.2f, median=%.1f' % (
        summary['size_stats']['min'], summary['size_stats']['max'], summary['size_stats']['mean'], summary['size_stats']['median']))
    print('Najčešće veličine (top):', ', '.join(f"{k} ({v})" for k, v in summary['top_size_counts'][:5]))
    print('Prazan skup:', 'prisutan' if summary['empty_present'] else 'nije')
    print('Broj povezanih komponenti (weakly connected):', summary['weakly_connected_components'])
    print('Graf je DAG:', 'da' if summary['is_dag'] else 'ne')
    print('Najduži lanac (longest path):', summary['longest_chain_nodes'])
    print('Nivo raspodele (prvih 10 nivoa):', summary['levels_sample'])
    print('Podrška studenata (tačna poklapanja stanja):', f"{summary['states_with_support']} stanja imaju bar jednog studenta; ukupno {summary['total_students_mapped']} studenata su tačno mapirani")


if __name__ == '__main__':
    main()
