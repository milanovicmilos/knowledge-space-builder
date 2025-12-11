import argparse
import configparser
import random
from typing import List

import neat
import pandas as pd

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend for Windows
    import matplotlib.pyplot as plt
    import networkx as nx
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from . import paths, evaluation, reporting, genome, output_utils

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


def load_response_patterns(path: str,
                           knowledge_items: int,
                           randomize: bool = True) -> List[str]:
    df = pd.read_csv(path, header=None)
    ncols = len(df.columns)

    if randomize:
        included_cols = list(random.sample(range(ncols), knowledge_items))
    else:
        included_cols = list(range(ncols))[:knowledge_items]

    df = df.iloc[:, included_cols]

    response_patterns = []
    for _, *row in df.itertuples():
        response = ''.join([str(i) for i in row])
        response_patterns.append(response)
    return response_patterns


def parse_config_file(config_filename: str) -> dict:
    config = configparser.ConfigParser()
    config.read(config_filename)
    return config['LearningSpaceGenome']


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

    num_items = int(config['knowledge_items'])
    response_patterns = load_response_patterns(path=args.data_path,
                                               knowledge_items=num_items,
                                               randomize=args.randomize_items)

    # In greedy mode, run NEAT for unlimited generations.
    generations = None if args.greedy else args.generations

    if args.greedy:
        print('\nRunning greedy NEAT.\n')
    else:
        print('\nRunning NEAT for {} generations.\n'.format(generations))

    optimal_ls = run_neat(generations=generations,
                          config_filename=args.config,
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
