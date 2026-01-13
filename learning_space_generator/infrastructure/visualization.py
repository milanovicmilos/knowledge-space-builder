import logging
import os

logger = logging.getLogger(__name__)

def save_graph_png(G, out_png):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except Exception:
        logger.warning('matplotlib not available; skipping prereq graph PNG')
        return

    import networkx as nx
    plt.figure(figsize=(10, 8))
    try:
        pos = nx.drawing.nx_agraph.graphviz_layout(G, prog='dot')
    except Exception:
        pos = nx.spring_layout(G, seed=1)
    nx.draw(G, pos, with_labels=True, node_size=80, font_size=6)
    os.makedirs(os.path.dirname(out_png) or '.', exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.close()
    logger.info('Saved prerequisite graph PNG to %s', out_png)


def save_hasse_diagram(poset_dict, out_png):
    """Save Hasse diagram (lattice poset) as PNG.
    
    Args:
        poset_dict: dict with 'states' and 'edges' keys (from lattice builder)
        out_png: output path for PNG file
    """
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except Exception:
        logger.warning('matplotlib not available; skipping lattice PNG')
        return

    import networkx as nx
    
    # Build graph from poset
    if isinstance(poset_dict, dict):
        states = poset_dict.get('states', [])
        edges = poset_dict.get('edges', [])
        
        G = nx.DiGraph()
        for s in states:
            G.add_node(s['id'], label=s.get('label', str(s['id'])))
        for e in edges:
            G.add_edge(e['from'], e['to'])
    else:
        # If it's already a graph, use it directly
        G = poset_dict
    
    plt.figure(figsize=(12, 10))
    try:
        pos = nx.drawing.nx_agraph.graphviz_layout(G, prog='dot')
    except Exception:
        pos = nx.spring_layout(G, seed=1)
    
    nx.draw(G, pos, with_labels=True, node_size=100, font_size=5, node_color='lightblue')
    os.makedirs(os.path.dirname(out_png) or '.', exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()
    logger.info('Saved Hasse diagram PNG to %s', out_png)
