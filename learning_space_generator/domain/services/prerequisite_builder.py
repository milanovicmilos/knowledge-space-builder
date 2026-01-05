import json
import os
import networkx as nx
import numpy as np
import logging

logger = logging.getLogger(__name__)


def build_prereq_graph(pred_probs, item_cols, pred_threshold=0.6, implication_threshold=0.85, min_known=10):
    # Robustly handle item_cols saved as 0-d object arrays
    try:
        item_arr = np.asarray(item_cols)
        if item_arr.ndim == 0:
            inner = item_arr.item()
            if isinstance(inner, (list, tuple, np.ndarray)):
                item_arr = np.asarray(inner, dtype=object)
            else:
                item_arr = np.asarray([inner], dtype=object)
    except Exception:
        item_arr = np.asarray(item_cols)

    binary = pred_probs >= pred_threshold
    # remove None or empty labels
    item_list = [str(x) for x in list(item_arr) if (x is not None and str(x).strip() != '')]
    n_items = len(item_list)
    G = nx.DiGraph()
    G.add_nodes_from(item_list)

    for b_idx in range(n_items):
        knows_b = binary[:, b_idx]
        n_knows_b = int(knows_b.sum())
        if n_knows_b < min_known:
            continue
        for a_idx in range(n_items):
            if a_idx == b_idx:
                continue
            knows_a = binary[:, a_idx]
            implication_rate = float((knows_b & knows_a).sum()) / float(n_knows_b)
            if implication_rate >= implication_threshold:
                G.add_edge(item_list[a_idx], item_list[b_idx], weight=implication_rate)

    try:
        if nx.is_directed_acyclic_graph(G):
            G = nx.algorithms.dag.transitive_reduction(G)
    except Exception:
        pass

    return G


def save_graph_json(G, out_json):
    mapping = {n: [] for n in G.nodes()}
    for u, v in G.edges():
        mapping[v].append(u)
    os.makedirs(os.path.dirname(out_json) or '.', exist_ok=True)
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)
    logger.info('Saved prerequisite JSON to %s', out_json)
