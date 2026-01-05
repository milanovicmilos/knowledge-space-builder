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
