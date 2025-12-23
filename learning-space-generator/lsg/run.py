import argparse
import configparser
import random
import tempfile
import os
from typing import List, Optional, Tuple
import logging
from pathlib import Path
import hashlib
import pickle

import neat
import pandas as pd
import numpy as np
from scipy.sparse.linalg import svds
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.metrics import silhouette_score

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend for Windows
    import matplotlib.pyplot as plt
    import networkx as nx
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from . import paths, output_utils
from .algorithms.neat import run_neat, LearningSpaceGenome

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

EARLY_STOPPING_PATIENCE = 20
DEFAULT_GENERATIONS = 15


def save_learning_space_graph(learning_space, outfile='graph.png') -> None:
    """Save learning space graph visualization.
    
    Supports multiple formats:
    - PNG: Uses graphviz if available, falls back to matplotlib
    - SVG: Uses graphviz if available
    - JPG/JPEG: Uses matplotlib
    - Without extension: Saves as PNG (with fallback)
    """
    
    # Try graphviz first if PNG or SVG requested
    if outfile.endswith(('.png', '.svg')):
        try:
            graph = learning_space.to_pydot_graph()
            if outfile.endswith('.png'):
                graph_image_bytes = graph.create_png(prog='dot', encoding='utf-8')
            else:  # SVG
                graph_image_bytes = graph.create_svg(encoding='utf-8')
            with open(outfile, 'wb') as fp:
                fp.write(graph_image_bytes)
            return
        except Exception as e:
            if not MATPLOTLIB_AVAILABLE:
                raise RuntimeError(
                    f"Cannot generate {outfile}: "
                    "graphviz not installed and matplotlib not available. "
                    f"Error: {e}"
                )
            # Fall through to matplotlib visualization
            print(f"[INFO] Graphviz not available. Using matplotlib visualization.")
    
    # Use matplotlib for visualization
    if not MATPLOTLIB_AVAILABLE:
        raise RuntimeError(
            "matplotlib is required for visualization on Windows without graphviz. "
            "Install with: pip install matplotlib networkx"
        )
    
    _save_graph_matplotlib(learning_space, outfile)


def _save_graph_matplotlib(learning_space, outfile: str) -> None:
    """Generate learning space graph visualization using matplotlib and networkx."""
    import matplotlib.pyplot as plt
    import networkx as nx
    
    # Get knowledge states and create graph
    knowledge_states = learning_space.knowledge_states(sort=True)
    
    # Create directed graph
    G = nx.DiGraph()
    
    # Add nodes with labels
    node_labels = {}
    for i, state in enumerate(knowledge_states):
        state_str = str(state)
        G.add_node(state_str)
        node_labels[state_str] = state_str
    
    # Add edges (adjacencies where distance = 1)
    for i, source_state in enumerate(knowledge_states[:-1]):
        for dst_state in knowledge_states[i + 1:]:
            if sum((source_state ^ dst_state)._bitarray) == 1:
                src = str(source_state)
                dst = str(dst_state)
                G.add_edge(src, dst)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Use spring layout for better visualization
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    
    # Draw network
    nx.draw_networkx_nodes(G, pos, node_color='lightblue', 
                          node_size=1500, ax=ax)
    nx.draw_networkx_edges(G, pos, edge_color='gray', 
                          arrows=True, arrowsize=20, 
                          connectionstyle="arc3,rad=0.1", ax=ax)
    nx.draw_networkx_labels(G, pos, node_labels, font_size=8, ax=ax)
    
    # Set title
    ax.set_title(f'Learning Space Graph\n'
                f'Nodes: {len(G.nodes())}, Edges: {len(G.edges())}, '
                f'Discrepancy: {learning_space.discrepancy():.1f}',
                fontsize=14, fontweight='bold')
    ax.axis('off')
    plt.tight_layout()
    
    # Save figure
    plt.savefig(outfile, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Graph visualization saved to '{outfile}' using matplotlib.")


def _infer_delimiter(path: str) -> str:
    """Infer CSV delimiter using a small sample; default to comma."""
    import csv

    with open(path, 'r', newline='') as fp:
        sample = ''.join([fp.readline() for _ in range(5)])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[',', ';', '\t'])
        return dialect.delimiter
    except Exception:
        return ','


def _identify_binary_columns(df: pd.DataFrame) -> List[str]:
    """Identify columns that contain only binary responses (0/1/NA)."""
    binary_cols = []
    for col in df.columns:
        series = df[col]
        unique_vals = {v for v in series.dropna().unique().tolist()}

        normalized = set()
        for v in unique_vals:
            if isinstance(v, (int, float)):
                normalized.add(int(v))
                continue
            s = str(v).strip()
            if s.isdigit():
                normalized.add(int(s))
            else:
                normalized.add(s)

        if normalized <= {0, 1}:
            binary_cols.append(col)
    return binary_cols


def _get_column_coverage(df: pd.DataFrame, binary_cols: List[str]) -> pd.Series:
    """Calculate coverage (% non-NA) for each binary column."""
    coverage = {}
    for col in binary_cols:
        non_na = df[col].notna().sum()
        coverage[col] = (non_na / len(df)) * 100
    return pd.Series(coverage).sort_values(ascending=False)


def _auto_select_k(mask_matrix: np.ndarray, k_min: int = 2, k_max: int = 8) -> int:
    """Pick K via silhouette on the availability mask; fallback to 2 on errors."""
    best_k = max(k_min, 2)
    best_score = -1.0
    # Subsample rows if dataset is huge for speed
    rows = mask_matrix
    if rows.shape[0] > 10000:
        rng = np.random.default_rng(42)
        idx = rng.choice(rows.shape[0], size=10000, replace=False)
        rows = rows[idx]
    for k in range(k_min, min(k_max, rows.shape[0] - 1) + 1):
        try:
            km = KMeans(n_clusters=k, n_init=10, random_state=42)
            labels = km.fit_predict(rows)
            score = silhouette_score(rows, labels)
            if score > best_score:
                best_score = score
                best_k = k
        except Exception:
            continue
    return best_k


def cluster_response_patterns(path: str,
                              min_coverage_in_cluster: float = 0.7,
                              max_k: int = 8,
                              min_cluster_rows: int = 50,
                              knowledge_items: Optional[int] = None,
                              randomize: bool = True) -> Tuple[list, dict]:
    """
    Cluster students by answered-items mask to form denser submatrices (domains).
    For each cluster, select columns with high in-cluster coverage, drop rows with
    missing in those columns, and emit complete binary response patterns.

    Returns: (clusters, global_metadata)
    clusters: List of dicts {id, rows, cols, response_patterns, item_names, stats}
    """
    sep = _infer_delimiter(path)
    logger.info(f"\n{'='*80}")
    logger.info("CLUSTERING STUDENTS TO FORM DENSE DOMAINS (no ALS)")
    logger.info(f"{'='*80}")
    logger.info(f"File: {Path(path).name}")
    logger.info(f"Separator: {repr(sep)}")

    df = pd.read_csv(path, sep=sep)
    logger.info(f"Loaded: {len(df):,} rows × {len(df.columns)} columns")

    all_binary = _identify_binary_columns(df)
    if not all_binary:
        raise ValueError('No binary response columns found.')
    logger.info(f"Binary response columns: {len(all_binary)}")

    # Optionally limit number of items
    if knowledge_items:
        if randomize:
            rng = np.random.default_rng(42)
            sel_idx = rng.choice(len(all_binary), size=min(knowledge_items, len(all_binary)), replace=False)
            selected_all = [all_binary[i] for i in sel_idx]
        else:
            selected_all = all_binary[:knowledge_items]
    else:
        selected_all = all_binary

    sub = df[selected_all]
    mask = sub.notna().astype(int).values

    # Auto-pick K
    k = _auto_select_k(mask, k_min=2, k_max=max_k)
    logger.info(f"Auto-selected K={k} clusters (silhouette on availability mask)")

    km = KMeans(n_clusters=k, n_init=10, random_state=42)
    labels = km.fit_predict(mask)

    clusters = []
    for cid in range(k):
        row_idx = np.where(labels == cid)[0]
        if row_idx.size < min_cluster_rows:
            logger.info(f"Skip cluster {cid}: too few rows ({row_idx.size} < {min_cluster_rows})")
            continue

        sub_df = sub.iloc[row_idx]
        cov = _get_column_coverage(sub_df, selected_all)
        chosen_cols = cov[cov >= (min_coverage_in_cluster * 100)].index.tolist()
        if len(chosen_cols) < 3:
            logger.info(f"Skip cluster {cid}: too few columns after coverage filter ({len(chosen_cols)})")
            continue

        block = sub_df[chosen_cols]
        # Drop rows with any NaN to avoid matrix completion
        block_complete = block.dropna(axis=0, how='any')
        if block_complete.shape[0] < min_cluster_rows // 2:
            logger.info(f"Skip cluster {cid}: not enough complete rows after dropna ({block_complete.shape[0]})")
            continue

        # Ensure binary 0/1
        block_bin = block_complete.applymap(lambda v: int(v) if str(v).strip().isdigit() else int(float(v)))
        patterns = [
            ''.join('1' if x == 1 else '0' for x in row_values)
            for row_values in block_bin.values.tolist()
        ]

        density = (block_complete.notna().sum().sum()) / (block_complete.shape[0] * block_complete.shape[1])
        clusters.append({
            'id': cid,
            'row_count': block_complete.shape[0],
            'col_count': block_complete.shape[1],
            'response_patterns': patterns,
            'item_names': chosen_cols,
            'stats': {
                'coverage_mean_percent': float(_get_column_coverage(block_complete, chosen_cols).mean()),
                'density': float(density)
            }
        })

    global_meta = {
        'total_rows': int(df.shape[0]),
        'total_binary_cols': int(len(all_binary)),
        'selected_cols': int(len(selected_all)),
        'formed_clusters': int(len(clusters))
    }
    return clusters, global_meta


def _pairwise_item_similarity(values_df: pd.DataFrame,
                              min_pairs: int = 500) -> np.ndarray:
    """Compute item-item similarity based on correctness correlation where both items observed.

    Returns an (m x m) similarity matrix in [0,1], NaNs treated as 0.
    """
    data = values_df
    m = data.shape[1]
    sim = np.zeros((m, m), dtype=float)
    cols = list(data.columns)
    # Pre-extract columns as arrays
    arrays = [data[c].values for c in cols]
    for i in range(m):
        ai = arrays[i]
        for j in range(i, m):
            aj = arrays[j]
            mask = (~pd.isna(ai)) & (~pd.isna(aj))
            n = int(np.sum(mask))
            if n < min_pairs:
                val = 0.0
            else:
                vi = ai[mask].astype(float)
                vj = aj[mask].astype(float)
                if np.std(vi) == 0 or np.std(vj) == 0:
                    val = 0.0
                else:
                    corr = float(np.corrcoef(vi, vj)[0, 1])
                    # Map [-1,1] -> [0,1]
                    val = max(0.0, min(1.0, 0.5 * (corr + 1.0)))
            sim[i, j] = sim[j, i] = val
    return sim


def item_cluster_response_patterns(path: str,
                                   items_min: Optional[int] = None,
                                   items_max: Optional[int] = None,
                                   row_coverage_thresh: float = 0.8,
                                   min_pairs: int = 500,
                                   max_item_clusters: int = 10,
                                   knowledge_items: Optional[int] = None,
                                   randomize: bool = True) -> Tuple[list, dict]:
    """
    PARTITION all items into K non-overlapping clusters via item similarity clustering.
    SVAKO pitanje ide u TAČNO JEDAN klaster. Zbir svih item-a u svim klasterima = ukupan broj item-a.
    
    K se bira automatski na osnovu silhouette score analize (higher = better separated clusters).
    
    Returns: clusters list with keys: response_patterns_iita, response_patterns_neat, item_names,
    and stats.
    """
    sep = _infer_delimiter(path)
    logger.info(f"\n{'='*80}")
    logger.info("ITEM PARTITIONING (svaki item u tačno jedan domain)")
    logger.info(f"{'='*80}")
    logger.info(f"File: {Path(path).name}")
    logger.info(f"Separator: {repr(sep)}")

    df = pd.read_csv(path, sep=sep)
    all_binary = _identify_binary_columns(df)
    if not all_binary:
        raise ValueError('No binary response columns found.')
    if knowledge_items:
        selected_all = all_binary[:knowledge_items]
    else:
        selected_all = all_binary

    sub = df[selected_all]
    m = len(selected_all)
    logger.info(f"Binary items to partition: {m}")

    # Analyze data sparsity to guide K selection range
    overall_density = sub.notna().sum().sum() / (sub.shape[0] * sub.shape[1])
    logger.info(f"Overall dataset density: {overall_density:.1%}")
    
    # AUTOMATIC MAX K based on number of items and minimum viable cluster size
    # Philosophy: 
    # - Min cluster size: 3 items (anything smaller is too trivial for prerequisite structure)
    # - Max cluster size: adaptive based on density (sparse → larger, dense → smaller)
    
    min_items_per_cluster = 3
    absolute_max_k = max(2, m // min_items_per_cluster)
    logger.info(f"Absolute maximum K based on {m} items: {absolute_max_k} (min {min_items_per_cluster} items/cluster)")
    
    # ADAPTIVE K RANGE - fully data-driven without magic numbers
    # Logic: Sparse data needs larger clusters to accumulate enough observations
    #        Dense data can afford smaller, more fine-grained domain separation
    
    if overall_density < 0.10:
        # Very sparse: need LARGE clusters (15-30 items each) to get reasonable density
        suggested_avg_size = 25
        k_range_min = max(2, m // 50)  # very conservative lower bound
        k_range_max = min(absolute_max_k, m // 10)  # larger clusters
        logger.info(f"Very sparse data ({overall_density:.1%}) → suggesting larger clusters (~{suggested_avg_size} items)")
    elif overall_density < 0.30:
        # Moderate: medium clusters (10-20 items each)
        suggested_avg_size = 15
        k_range_min = max(2, m // 30)
        k_range_max = min(absolute_max_k, m // 6)
        logger.info(f"Moderate density ({overall_density:.1%}) → suggesting medium clusters (~{suggested_avg_size} items)")
    else:
        # Dense: can afford small clusters (5-10 items each)
        suggested_avg_size = 8
        k_range_min = max(2, m // 20)
        k_range_max = min(absolute_max_k, m // 4)
        logger.info(f"Dense data ({overall_density:.1%}) → suggesting smaller clusters (~{suggested_avg_size} items)")
    
    logger.info(f"Data-driven K range: [{k_range_min}, {k_range_max}]")
    
    # Use data-driven range as primary K selection boundaries
    k_min = k_range_min
    k_max = k_range_max
    
    # Optional: user can narrow the range with explicit bounds
    if items_min is not None and items_max is not None:
        target_avg_size = (items_min + items_max) / 2.0
        k_from_target = max(2, int(round(m / target_avg_size)))
        # Expand range around user target
        k_min = max(2, min(k_min, k_from_target - 3))
        k_max = min(absolute_max_k, max(k_max, k_from_target + 3))
        logger.info(f"User-specified size range [{items_min}, {items_max}] → K target ~{k_from_target}")
    
    # Override: user can explicitly limit K range via --max-item-clusters
    if max_item_clusters is not None:
        k_max = min(absolute_max_k, max_item_clusters)
        logger.info(f"User override: max K limited to {max_item_clusters}")

    # Compute item-item similarity based on co-observation patterns
    logger.info(f"Computing pairwise item similarity (min pairs={min_pairs})...")
    sim_matrix = _pairwise_item_similarity(sub, min_pairs=min_pairs)
    dist_matrix = 1.0 - sim_matrix
    np.fill_diagonal(dist_matrix, 0)  # Ensure diagonal is zero for precomputed metric
    
    logger.info(f"AUTO K SELECTION: testing K from {k_min} to {k_max} via silhouette score...")
    
    best_k = k_min
    best_score = -1.0
    scores = {}
    
    for k_test in range(k_min, k_max + 1):
        try:
            from sklearn.cluster import AgglomerativeClustering
            clusterer = AgglomerativeClustering(n_clusters=k_test, linkage='average')
            labels_test = clusterer.fit_predict(dist_matrix)
            
            # Silhouette score: measures how compact and separated clusters are
            # Range [-1, 1]: higher is better
            score = silhouette_score(dist_matrix, labels_test, metric='precomputed')
            scores[k_test] = score
            
            sizes = [np.sum(labels_test == cid) for cid in range(k_test)]
            logger.info(f"  K={k_test}: silhouette={score:.3f}, sizes={sorted(sizes)}")
            
            if score > best_score:
                best_score = score
                best_k = k_test
        except Exception as e:
            logger.warning(f"  K={k_test}: failed ({e})")
            continue
    
    k_optimal = best_k
    logger.info(f"✓ AUTO SELECTED K={k_optimal} (silhouette={scores.get(k_optimal, 0):.3f})")
    
    # Final clustering with optimal K
    clusterer = AgglomerativeClustering(n_clusters=k_optimal, linkage='average')
    item_labels = clusterer.fit_predict(dist_matrix)
    
    # Grupiši items po labelama
    clusters_items = []
    for cid in range(k_optimal):
        idxs = np.where(item_labels == cid)[0]
        cols = [selected_all[i] for i in idxs]
        clusters_items.append(cols)
    
    # Provera: da li smo particionisali SVE item-e?
    total_assigned = sum(len(c) for c in clusters_items)
    logger.info(f"Partition complete: {len(clusters_items)} clusters, {total_assigned}/{m} items assigned")
    if total_assigned != m:
        logger.warning(f"GREŠKA: Nije svih {m} item-a particionisano! Assigned={total_assigned}")
    
    # Prikaži veličine klastera
    sizes = [len(c) for c in clusters_items]
    logger.info(f"Cluster sizes: min={min(sizes)}, max={max(sizes)}, avg={np.mean(sizes):.1f}")
    logger.info(f"Sizes: {sizes}")
    logger.info(f"Sizes: {sizes}")

    # Za svaki klaster, formiraj response patterns
    clusters = []
    for cid, cols in enumerate(clusters_items):
        block = sub[cols]
        # Keep rows that have at least row_coverage_thresh observed within these columns
        row_obs = block.notna().mean(axis=1)
        keep = row_obs >= row_coverage_thresh
        block_kept = block[keep]
        
        if block_kept.shape[0] < 50:  # minimum students per cluster
            logger.warning(f"Cluster {cid} ({len(cols)} items): samo {block_kept.shape[0]} studenata sa >{row_coverage_thresh*100:.0f}% coverage - preskačem")
            continue

        # IITA patterns: complete rows only
        block_complete = block_kept.dropna(axis=0, how='any')
        
        # Encode for IITA (0/1) and for NEAT (with '-')
        def encode_binary(df_part: pd.DataFrame) -> list:
            if df_part.empty:
                return []
            bb = df_part.map(lambda v: int(v) if pd.notna(v) and str(v).strip().isdigit() else (int(float(v)) if pd.notna(v) else 0))
            return [''.join('1' if x == 1 else '0' for x in row) for row in bb.values.tolist()]

        def encode_missing(df_part: pd.DataFrame) -> list:
            vals = df_part
            patterns = []
            for row in vals.values.tolist():
                out = []
                for v in row:
                    if pd.isna(v):
                        out.append('-')
                    else:
                        try:
                            iv = int(v)
                        except Exception:
                            iv = int(float(v))
                        out.append('1' if iv == 1 else '0')
                patterns.append(''.join(out))
            return patterns

        rp_iita = encode_binary(block_complete)
        rp_neat = encode_missing(block_kept)
        
        density_kept = block_kept.notna().sum().sum() / (block_kept.shape[0] * block_kept.shape[1])

        clusters.append({
            'item_names': cols,
            'row_count_kept': int(block_kept.shape[0]),
            'row_count_complete': int(block_complete.shape[0]),
            'col_count': int(len(cols)),
            'response_patterns_iita': rp_iita,
            'response_patterns_neat': rp_neat,
            'stats': {
                'row_coverage_thresh': float(row_coverage_thresh),
                'avg_row_obs_kept_percent': float(row_obs[keep].mean() * 100.0),
                'density_kept': float(density_kept)
            }
        })
        
        logger.info(f"  Cluster {cid}: {len(cols)} items, {block_kept.shape[0]} students (kept), {block_complete.shape[0]} complete, density={density_kept:.2%}")

    meta = {
        'total_rows': int(df.shape[0]),
        'total_binary_cols': int(len(all_binary)),
        'selected_cols': int(len(selected_all)),
        'formed_clusters': int(len(clusters)),
        'k_optimal': int(k_optimal),
        'all_items': selected_all,  # ADD: all items for tracking isolated
        'clusters_items': clusters_items  # ADD: raw cluster partitions
    }
    return clusters, meta


def _select_columns(coverage: pd.Series,
                   min_coverage: float = 5.0,
                   max_items: Optional[int] = None) -> List[str]:
    """Select columns based on coverage thresholds."""
    selected = coverage[coverage >= min_coverage].index.tolist()
    if max_items and len(selected) > max_items:
        selected = selected[:max_items]
    return selected


def _parse_knowledge_items(raw_value: str) -> Optional[int]:
    """Support integer or the keyword 'auto'/'all' for using all columns."""
    if raw_value is None:
        return None
    value = str(raw_value).strip().lower()
    if value in ('auto', 'all', ''):
        return None
    return int(raw_value)


def _stratified_sample(df: pd.DataFrame,
                      sample_size: Optional[int],
                      stratify_col: str = 'T_Grade') -> pd.DataFrame:
    """Sample dataframe, optionally stratified by a column (e.g., grade)."""
    if sample_size is None or sample_size >= len(df):
        return df
    if stratify_col and stratify_col in df.columns:
        return df.groupby(stratify_col, group_keys=False).apply(
            lambda x: x.sample(min(len(x), max(1, int(sample_size * len(x) / len(df)))))
        ).head(sample_size)
    return df.sample(n=min(sample_size, len(df)), random_state=42)


def _get_cache_path(data_path: str, 
                   selected_cols: List[str],
                   sample_size: Optional[int],
                   als_rank: int,
                   als_iterations: int) -> Path:
    """
    Generiše jedinstvenu cache putanju za completed matrix.
    
    Cache key: hash(data_path + selected_columns + sample_size + ALS params)
    """
    cache_dir = Path('output/cache')
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Kreiraj jedinstveni hash od parametara
    cache_key = f"{data_path}|{sorted(selected_cols)}|{sample_size}|{als_rank}|{als_iterations}"
    cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
    
    return cache_dir / f"matrix_completion_{cache_hash}.npy"


def load_response_patterns(path: str,
                           knowledge_items: Optional[int],
                           randomize: bool = True) -> Tuple[List[str], dict]:
    """
    Load response patterns with missing values encoded as '-' for NEAT evaluator.
    
    This is the simple no-ALS mode: sparse patterns with '-' for missing data.
    NEAT's missing-aware evaluator will handle these appropriately.
    
    Args:
        path: Path to CSV file
        knowledge_items: Number of items (None = use ALL columns)
        randomize: Randomly select items if knowledge_items < total
        
    Returns:
        (response_patterns, metadata)
    """
    
    sep = _infer_delimiter(path)
    logger.info(f'\n{"="*80}')
    logger.info(f'LOADING DATA (missing-aware mode)')
    logger.info(f'{"="*80}')
    logger.info(f'File: {Path(path).name}')
    logger.info(f'Separator: {repr(sep)}')
    
    df = pd.read_csv(path, sep=sep)
    logger.info(f'Loaded: {len(df):,} rows × {len(df.columns)} columns')
    
    # Identify binary response columns
    all_binary = _identify_binary_columns(df)
    logger.info(f'Binary response columns: {len(all_binary)}')
    
    if not all_binary:
        raise ValueError('No binary response columns found.')
    
    # Select columns
    selected_cols = all_binary[:knowledge_items] if knowledge_items else all_binary
    logger.info(f'Using {len(selected_cols)} columns')
    
    # Encode sparse patterns with '-' for missing
    logger.info('Encoding missing entries as "-" for NEAT evaluator.')
    vals = df[selected_cols]
    def encode_row(row):
        out = []
        for v in row:
            if pd.isna(v):
                out.append('-')
            else:
                try:
                    iv = int(v)
                except Exception:
                    iv = int(float(v))
                out.append('1' if iv == 1 else '0')
        return ''.join(out)
    response_patterns = [encode_row(r) for r in vals.values.tolist()]
    
    # Statistics
    unique_patterns = len(set(response_patterns))
    logger.info(f'\n{"="*80}')
    logger.info(f'FINAL DATASET')
    logger.info(f'{"="*80}')
    logger.info(f'Total patterns: {len(response_patterns):,}')
    logger.info(f'Unique patterns: {unique_patterns:,} ({100*unique_patterns/len(response_patterns):.1f}% diversity)')
    logger.info(f'Pattern length: {len(response_patterns[0])} items')
    logger.info(f'{"="*80}\n')
    
    metadata = {
        'total_rows': len(df),
        'selected_columns': selected_cols,
        'num_items': len(selected_cols),
        'valid_patterns': len(response_patterns),
        'unique_patterns': unique_patterns
    }

    return response_patterns, metadata


def parse_config_file(config_filename: str) -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    config.read(config_filename)
    return config


def _materialize_config(config: configparser.ConfigParser,
                        base_path: str,
                        knowledge_items: int) -> str:
    """Ensure NEAT config has the resolved knowledge_items value."""
    current = config['LearningSpaceGenome'].get('knowledge_items')
    if current == str(knowledge_items):
        return base_path

    config_copy = configparser.ConfigParser()
    config_copy.read_dict({section: dict(config[section]) for section in config.sections()})
    config_copy['LearningSpaceGenome']['knowledge_items'] = str(knowledge_items)

    tmp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False)
    config_copy.write(tmp_file)
    tmp_file.close()
    return tmp_file.name


def parse_command_line_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser('Run learning space generation algorithms (NEAT or IITA) '
                                     'to analyze response patterns and generate learning structures.')
    parser.add_argument('-c', '--config',
                        type=str, default=paths.DEFAULT_CONFIG_PATH,
                        help='Path to config file.')
    parser.add_argument('-d', '--data-path',
                        type=str, default=paths.RESPONSES_PATH,
                        help='Path to the CSV file with response patterns.')
    parser.add_argument('-g', '--generations',
                        type=int, default=DEFAULT_GENERATIONS,
                        help='[NEAT only] Number of generations.')
    parser.add_argument('-t', '--patience',
                        type=int, default=EARLY_STOPPING_PATIENCE,
                        help='[NEAT only] Number of generations without fitness improvement '
                             'before algorithm stops.')
    parser.add_argument('-i', '--png',
                        type=str,
                        help='Output filename (or path) for learning space graph PNG image. '
                             'If only filename given, saves to output/visualizations/.')
    parser.add_argument('-l', '--plot', action='store_true',
                        help='[NEAT only] Show the best learning space during evolution.')
    parser.add_argument('-j', '--json',
                        type=str, default='learning_space.json',
                        help='Output filename (or path) for learning space JSON. '
                             'If only filename given, saves to output/data/.')
    parser.add_argument('-p', '--parallel', action='store_true',
                        help='[NEAT only] Enable parallel genome evaluation.')
    parser.add_argument('-s', '--silent', action='store_true',
                        help='Supress any output to stdout.')
    parser.add_argument('-r', '--randomize-items', action='store_true',
                        help='Randomly load question columns from responses data file.')
    parser.add_argument('-y', '--greedy', action='store_true',
                        help='[NEAT only] Run algorithm until the first complete, valid learning '
                             'space is created.')
    parser.add_argument('--cluster', action='store_true',
                        help='Partition items into non-overlapping domains via similarity clustering.')
    parser.add_argument('--items-min', type=int, default=None,
                        help='[items mode] Minimum items per item cluster. Auto-computed if not specified.')
    parser.add_argument('--items-max', type=int, default=None,
                        help='[items mode] Maximum items per item cluster. Auto-computed if not specified.')
    parser.add_argument('--row-coverage-thresh', type=float, default=0.8,
                        help='[items mode] Minimum per-row observed fraction within item cluster.')
    parser.add_argument('--min-pairs', type=int, default=500,
                        help='[items mode] Minimum co-observed pairs to compute item correlation.')
    parser.add_argument('--max-item-clusters', type=int, default=None,
                        help='[items mode] Max number of item clusters to attempt. '
                             'If not set, automatically determines based on data (recommended).')
    parser.add_argument('--missing-match-reward', type=float, default=0.0,
                        help='[NEAT only] Reward for matches on observed entries.')
    parser.add_argument('--missing-mismatch-penalty', type=float, default=1.0,
                        help='[NEAT only] Penalty for mismatches on observed entries.')
    return parser.parse_args()


if __name__ == '__main__':
    # Initialize output directory structure
    output_utils.ensure_output_dirs()
    
    args = parse_command_line_args()
    
    config = parse_config_file(config_filename=args.config)

    num_items = _parse_knowledge_items(config['LearningSpaceGenome'].get('knowledge_items'))
    
    # ============================================================
    # DATA INGESTION: ITEM CLUSTERING vs FULL DATASET
    # ============================================================
    clustered = None
    if args.cluster:
        item_clusters, global_meta = item_cluster_response_patterns(
            path=args.data_path,
            items_min=args.items_min,
            items_max=args.items_max,
            row_coverage_thresh=args.row_coverage_thresh,
            min_pairs=args.min_pairs,
            max_item_clusters=args.max_item_clusters,
            knowledge_items=num_items,
            randomize=args.randomize_items
        )
        if not item_clusters:
            raise SystemExit("No item clusters formed. Try lowering --row-coverage-thresh.")
        logger.info(f"Formed {len(item_clusters)} item clusters; proceeding per-cluster.")
        clustered = item_clusters
        actual_num_items = clustered[0]['col_count']
    else:
        response_patterns, metadata = load_response_patterns(
            path=args.data_path,
            knowledge_items=num_items,
            randomize=args.randomize_items
        )

        logger.info(f'\n=== Data Loading Summary ===')
        logger.info(f'Items selected: {metadata["num_items"]}')
        logger.info(f'Valid students: {metadata["valid_patterns"]:,}')
        logger.info(f'Unique patterns: {metadata["unique_patterns"]:,}')
        logger.info(f'Mean coverage: {metadata["coverage_mean"]:.1f}%')
        actual_num_items = metadata['num_items']
    
    # ============================================================
    # RUN NEAT ALGORITHM
    # ============================================================
    
    if not args.cluster:
        # ============================================================
        # NEAT (ORIGINAL ALGORITHM)
        # ============================================================
        # Verify config knowledge_items matches actual data
        config_knowledge_items_str = config['LearningSpaceGenome'].get('knowledge_items', '').strip().lower()
    
        # Parse config value (može biti 'all', 'auto', ili broj)
        if config_knowledge_items_str in ('all', 'auto', ''):
            config_num_items = None  # Auto-detect
        else:
            config_num_items = int(config_knowledge_items_str)
    
        if config_num_items is None or config_num_items != actual_num_items:
            logger.info(f'Config has {config_num_items or "auto"} items, using {actual_num_items} from data')
            
            # Create temporary config with correct number of items
            import tempfile
            config_copy = configparser.ConfigParser()
            config_copy.read_dict({section: dict(config[section]) for section in config.sections()})
            config_copy['LearningSpaceGenome']['knowledge_items'] = str(actual_num_items)
        
            tmp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False)
            config_copy.write(tmp_file)
            tmp_file.close()
            config_file_to_use = tmp_file.name
            logger.info(f'Using temporary config: {config_file_to_use}')
        else:
            config_file_to_use = args.config
            logger.info(f'Config matches data ({actual_num_items} items)')

        # In greedy mode, run NEAT for unlimited generations.
        generations = None if args.greedy else args.generations

        if args.greedy:
            print('\nRunning greedy NEAT.\n')
        else:
            print('\nRunning NEAT for {} generations.\n'.format(generations))

        optimal_ls = run_neat(generations=generations,
                              config_filename=config_file_to_use,
                              responses=response_patterns,
                              early_stopping_patience=args.patience,
                              verbose=not args.silent,
                              plot_best=args.plot,
                      parallel=args.parallel,
                      is_greedy=args.greedy,
                      mismatch_penalty=args.missing_mismatch_penalty,
                      match_reward=args.missing_match_reward,
                      item_names=metadata.get('selected_columns', None))

        if not optimal_ls.is_valid():
            print('\n[WARNING] Learning space is not valid.')

        if args.json:
            # Use output/data/ directory if no path specified
            json_path = args.json if '/' in args.json or '\\' in args.json else output_utils.get_data_path(args.json)
            with open(json_path, 'w') as fp:
                fp.write(optimal_ls.to_json())
                print(f"\nThe best learning space graph JSON saved to '{json_path}'")

        if args.png:
            # Use output/visualizations/ directory if no path specified
            png_path = args.png if '/' in args.png or '\\' in args.png else output_utils.get_visualization_path(args.png)
            save_learning_space_graph(learning_space=optimal_ls, outfile=png_path)
            print(f"The best learning space graph PNG saved to '{png_path}'")

    else:
        # ============================================================
        # CLUSTERED FLOW (PER-CLUSTER IITA or NEAT) - students or items
        # ============================================================
        results_index = []
        for cluster in clustered:
            # Normalize cluster structure for both modes
            if 'id' in cluster:
                cid = cluster['id']
            else:
                # for item clusters, synthesize ID by index
                cid = clustered.index(cluster)

            items = cluster['item_names']
            if 'response_patterns' in cluster:
                # students-mode cluster
                rp_iita = cluster['response_patterns']  # already complete
                rp_neat = cluster['response_patterns']  # same, no missing
                row_info = f"rows={cluster['row_count']}"
            else:
                rp_iita = cluster['response_patterns_iita']
                rp_neat = cluster['response_patterns_neat']
                row_info = f"rows_kept={cluster['row_count_kept']}, rows_complete={cluster['row_count_complete']}"

            logger.info(f"\n--- Cluster {cid}: {row_info} cols={cluster['col_count']}")

            # NEAT per cluster - build temp config with correct items
            tmp_cfg = _materialize_config(config, base_path=args.config, knowledge_items=len(items))

            generations = None if args.greedy else args.generations
            optimal_ls = run_neat(generations=generations,
                                      config_filename=tmp_cfg,
                                      responses=rp_neat,
                                      early_stopping_patience=args.patience,
                                      verbose=not args.silent,
                                      plot_best=False,
                                      parallel=args.parallel,
                                      is_greedy=args.greedy,
                                      mismatch_penalty=args.missing_mismatch_penalty,
                                      match_reward=args.missing_match_reward,
                                      item_names=items)

            png_path = None
            if args.png:
                base = Path(args.png)
                name = base.stem + f"_cluster{cid}" + base.suffix
                # Use temp file for intermediate clusters (final merged result goes to args.png)
                import tempfile
                png_path = tempfile.mktemp(suffix=f'_cluster{cid}.png')
                save_learning_space_graph(learning_space=optimal_ls, outfile=png_path)

            json_path = None
            if args.json:
                base = Path(args.json)
                name = base.stem + f"_cluster{cid}" + base.suffix
                # Use temp file for intermediate clusters (final merged result goes to args.json)
                import tempfile
                json_path = tempfile.mktemp(suffix=f'_cluster{cid}.json')
                with open(json_path, 'w') as fp:
                    fp.write(optimal_ls.to_json())

            results_index.append({'cluster': cid, 'algo': 'neat', 'json': json_path, 'png': png_path, 'stats': cluster['stats']})

        # Save simple index file (use /tmp for Docker read-only volumes)
        try:
            index_path = output_utils.get_data_path('cluster_results_index.json')
            with open(index_path, 'w', encoding='utf-8') as f:
                import json as _json
                _json.dump({'clusters': results_index}, f, ensure_ascii=False, indent=2)
            logger.info(f"\n✓ Clustered analysis complete. Index saved to {index_path}")
        except (OSError, PermissionError):
            # Fallback to /tmp if output directory is read-only
            import tempfile
            import json as _json
            index_path = tempfile.mktemp(suffix='_cluster_results_index.json')
            with open(index_path, 'w', encoding='utf-8') as f:
                _json.dump({'clusters': results_index}, f, ensure_ascii=False, indent=2)
            logger.info(f"\n✓ Clustered analysis complete. Index saved to {index_path}")

        # Create structured multi-level knowledge space output
        if args.json and results_index:
            import json as _json
            
            # Build proper hierarchical structure
            structured_output = {
                "metadata": {
                    "total_items": len(global_meta['all_items']),
                    "num_clusters": len(global_meta['clusters_items']),
                    "algorithm": "NEAT",
                    "clustering_method": "hierarchical_agglomerative",
                    "k_optimal": global_meta['k_optimal']
                },
                "clusters": [],
                "isolated_items": [],
                "merged_learning_space": {}
            }
            
            # Collect all items that appear in processed clusters
            items_in_processed = set()
            
            # Process each successfully analyzed cluster
            for item in results_index:
                cluster_info = {
                    "cluster_id": item['cluster'],
                    "items": clustered[item['cluster']]['item_names'],
                    "num_items": len(clustered[item['cluster']]['item_names']),
                    "num_students": clustered[item['cluster']]['row_count_kept'],
                    "num_complete": clustered[item['cluster']]['row_count_complete'],
                    "density": clustered[item['cluster']]['stats']['density_kept'],
                    "learning_space": None
                }
                
                items_in_processed.update(clustered[item['cluster']]['item_names'])
                
                # Load cluster's learning space
                if item['json'] and os.path.exists(item['json']):
                    with open(item['json'], 'r') as f:
                        cluster_ls = _json.load(f)
                        cluster_info['learning_space'] = cluster_ls
                        cluster_info['num_states'] = len(cluster_ls)
                        
                        # Add to merged space
                        structured_output['merged_learning_space'].update(cluster_ls)
                
                structured_output['clusters'].append(cluster_info)
            
            # Find isolated items: items in original clusters but NOT in processed results
            # (due to insufficient data / skipped clusters)
            all_items_set = set(global_meta['all_items'])
            isolated = all_items_set - items_in_processed
            
            # Add singleton states for isolated items
            for item in sorted(isolated):
                singleton_state = f"{{{item}}}"
                structured_output['isolated_items'].append(item)
                # Add to merged space: {} -> {item}
                if "{}" not in structured_output['merged_learning_space']:
                    structured_output['merged_learning_space']["{}"] = []
                if singleton_state not in structured_output['merged_learning_space']["{}"] :
                    structured_output['merged_learning_space']["{}"].append(singleton_state)
            
            structured_output['metadata']['items_in_clusters'] = len(items_in_processed)
            structured_output['metadata']['isolated_items'] = len(isolated)
            
            with open(args.json, 'w') as f:
                _json.dump(structured_output, f, ensure_ascii=False, indent=2)
            
            logger.info(f"\n✓ Structured knowledge space saved to {args.json}")
            logger.info(f"  Total items: {len(all_items_set)}")
            logger.info(f"  Items in processed clusters: {len(items_in_processed)}")
            logger.info(f"  Isolated items (no data): {len(isolated)}")
            logger.info(f"  Total states: {len(structured_output['merged_learning_space'])}")
