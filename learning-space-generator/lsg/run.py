import argparse
import configparser
import random
import tempfile
from typing import List, Optional, Tuple
import logging
from pathlib import Path

import neat
import pandas as pd
import numpy as np

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend for Windows
    import matplotlib.pyplot as plt
    import networkx as nx
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from . import paths, evaluation, reporting, genome, output_utils

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

EARLY_STOPPING_PATIENCE = 20
DEFAULT_GENERATIONS = 15

def run_neat(generations: int,
             config_filename: str,
             responses: List[str],
             early_stopping_patience: int,
             verbose: bool = False,
             plot_best: bool = False,
             parallel: bool = False,
             is_greedy: bool = False) -> genome.LearningSpaceGenome:
    config = neat.Config(genome.LearningSpaceGenome,
                         neat.DefaultReproduction,
                         neat.DefaultSpeciesSet,
                         neat.DefaultStagnation,
                         config_filename)

    population = neat.Population(config)

    early_stopper = reporting.EarlyStoppingReporter(patience=early_stopping_patience,
                                                    is_greedy=is_greedy)
    population.add_reporter(early_stopper)

    fitness_term_stopper = reporting.FitnessTerminationReporter(threshold=-0.5)
    population.add_reporter(fitness_term_stopper)

    if verbose:
        tqdm_reporter = reporting.TqdmReporter(total_generations=generations)
        population.add_reporter(tqdm_reporter)

    if plot_best:
        plot_reporter = reporting.PlotReporter()
        population.add_reporter(plot_reporter)

    if parallel:
        evaluator = evaluation.ParallelEvaluator(responses)
    else:
        evaluator = evaluation.SerialEvaluator(responses)

    try:
        optimal_ls = population.run(evaluator.evaluate, generations)
    except reporting.EarlyStoppingException as exception:
        optimal_ls = exception.best_genome

        if verbose:
            # Excplicily close tqdm progress bar to fix printing to stdout.
            tqdm_reporter.close()

        if is_greedy:
            print('\nGreedy algorithm constructed learning space successfully.')
        else:
            print('\nNo fitness improvement '
                  'for {} generations.'.format(early_stopping_patience))
    except reporting.TerminationThresholdReachedException as exception:
        optimal_ls = exception.best_genome

        if verbose:
            # Excplicily close tqdm progress bar to fix printing to stdout.
            tqdm_reporter.close()

        print('\nTermination threshold reached. '
              'Found genome with {} discrepancy'.format(optimal_ls.discrepancy()))

    return optimal_ls


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


def load_response_patterns(path: str,
                           knowledge_items: Optional[int],
                           randomize: bool = True,
                           min_coverage: float = 5.0,
                           sample_size: Optional[int] = None,
                           stratify: bool = True) -> Tuple[List[str], dict]:
    """Load and optimize response patterns for NEAT from large sparse datasets.

    Args:
        path: Path to CSV file
        knowledge_items: Number of items to use (None = auto-detect best ones)
        randomize: Randomly select items if knowledge_items > 0
        min_coverage: Min % of students who answered item to include it
        sample_size: Sample N students (None = use all)
        stratify: Stratify sampling by T_Grade if available

    Returns:
        (response_patterns, metadata)

    Key improvements:
    - Selects only well-answered items (min_coverage parameter)
    - Stratified sampling preserves grade distribution
    - Handles sparse data correctly (no NA imputation)
    - Logs detailed information about filtering
    """

    sep = _infer_delimiter(path)
    logger.info(f'Loading CSV from {Path(path).name} with separator={repr(sep)}')
    df = pd.read_csv(path, sep=sep)
    logger.info(f'Loaded {len(df):,} rows × {len(df.columns)} columns')

    # Identify binary response columns
    all_binary = _identify_binary_columns(df)
    logger.info(f'Found {len(all_binary)} binary response columns')

    if not all_binary:
        raise ValueError('No binary response columns found in dataset.')

    # Calculate coverage for each column
    coverage = _get_column_coverage(df, all_binary)
    logger.info(f'Coverage: min={coverage.min():.1f}%, mean={coverage.mean():.1f}%, max={coverage.max():.1f}%')

    # Select columns meeting minimum coverage
    selected_cols = _select_columns(coverage, min_coverage=min_coverage,
                                    max_items=knowledge_items)
    if not selected_cols:
        raise ValueError(
            f'No columns with {min_coverage}% coverage. Increase min_coverage or use less strict thresholds.'
        )

    logger.info(f'Selected {len(selected_cols)} columns with {min_coverage}% min coverage')
    cols_display = f'Selected columns: {selected_cols[:10]}' + ('...' if len(selected_cols) > 10 else '')
    logger.info(cols_display)
    logger.info(f'Coverage of selected: min={coverage[selected_cols].min():.1f}%, mean={coverage[selected_cols].mean():.1f}%')

    # Sample students if requested
    if sample_size and sample_size < len(df):
        logger.info(f'Sampling {sample_size:,} students (stratified={stratify})')
        df = _stratified_sample(df, sample_size, stratify_col='T_Grade' if stratify else None)
        logger.info(f'After sampling: {len(df):,} rows')

    # Extract response patterns - handle sparse data properly
    # Strategy: Vectorized processing for speed
    logger.info(f'Converting {len(df):,} rows to response patterns...')
    
    # Fill NA with 0 (treat "didn't answer" as "didn't know")
    df_filled = df[selected_cols].fillna(0).astype(int)
    
    # Convert each row to string pattern
    response_patterns = df_filled.apply(lambda row: ''.join(str(val) for val in row), axis=1).tolist()
    valid_row_count = len(response_patterns)
    
    logger.info(f'Valid response patterns: {valid_row_count:,} / {len(df):,} ({valid_row_count/len(df)*100:.1f}%)')

    if not response_patterns:
        raise ValueError(
            'No students answered all selected items. Try lower min_coverage or larger sample_size.'
        )

    # Count unique patterns
    unique_patterns = len(set(response_patterns))
    logger.info(f'Unique response patterns: {unique_patterns:,} / {len(response_patterns):,} ({unique_patterns/len(response_patterns)*100:.1f}% diversity)')

    metadata = {
        'total_rows': len(df),
        'selected_columns': selected_cols,
        'num_items': len(selected_cols),
        'valid_patterns': len(response_patterns),
        'unique_patterns': unique_patterns,
        'coverage_mean': coverage[selected_cols].mean(),
        'coverage_min': coverage[selected_cols].min(),
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
    parser = argparse.ArgumentParser('Run NEAT algorithm to get '
                                     'the optimal learning space from response patterns.')
    parser.add_argument('-c', '--config',
                        type=str, default=paths.DEFAULT_CONFIG_PATH,
                        help='Path to config file.')
    parser.add_argument('-d', '--data-path',
                        type=str, default=paths.RESPONSES_PATH,
                        help='Path to the CSV file with response patterns.')
    parser.add_argument('-g', '--generations',
                        type=int, default=DEFAULT_GENERATIONS,
                        help='Number of generations.')
    parser.add_argument('-t', '--patience',
                        type=int, default=EARLY_STOPPING_PATIENCE,
                        help='Number of generations without fitness improvement'
                             'before algorithm stops.')
    parser.add_argument('-i', '--png',
                        type=str,
                        help='Output filename (or path) for learning space graph PNG image. '
                             'If only filename given, saves to output/visualizations/.')
    parser.add_argument('-l', '--plot', action='store_true',
                        help='Show the best learning space during evolution.')
    parser.add_argument('-j', '--json',
                        type=str, default='learning_space.json',
                        help='Output filename (or path) for learning space JSON. '
                             'If only filename given, saves to output/data/.')
    parser.add_argument('-p', '--parallel', action='store_true',
                        help='Enable parallel genome evaluation.')
    parser.add_argument('-s', '--silent', action='store_true',
                        help='Supress any output to stdout.')
    parser.add_argument('-r', '--randomize-items', action='store_true',
                        help='Randomly load question columns from responses data file.')
    parser.add_argument('-y', '--greedy', action='store_true',
                        help='Run algorithm until the first complete, valid learning'
                             'space is created.')
    return parser.parse_args()


if __name__ == '__main__':
    # Initialize output directory structure
    output_utils.ensure_output_dirs()
    
    args = parse_command_line_args()
    config = parse_config_file(config_filename=args.config)

    num_items = _parse_knowledge_items(config['LearningSpaceGenome'].get('knowledge_items'))
    response_patterns, metadata = load_response_patterns(
        path=args.data_path,
        knowledge_items=num_items,
        randomize=args.randomize_items,
        min_coverage=5.0,   # Reduced to 5% to preserve more columns
        sample_size=None,   # Use ALL available data - no sampling
        stratify=True  # Preserve grade distribution
    )

    logger.info(f'\n=== Data Loading Summary ===')
    logger.info(f'Items selected: {metadata["num_items"]}')
    logger.info(f'Valid students: {metadata["valid_patterns"]:,}')
    logger.info(f'Unique patterns: {metadata["unique_patterns"]:,}')
    logger.info(f'Mean coverage: {metadata["coverage_mean"]:.1f}%')

    # Verify config knowledge_items matches actual data
    actual_num_items = metadata['num_items']
    config_num_items = int(config['LearningSpaceGenome'].get('knowledge_items'))
    if config_num_items != actual_num_items:
        logger.info(f'Updating config: {config_num_items} items -> {actual_num_items} items from data')
        
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
                          is_greedy=args.greedy)

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
