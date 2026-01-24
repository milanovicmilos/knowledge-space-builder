import matplotlib.pyplot as plt
import networkx as nx
import json
from learning_space_generator.app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class VisualizationService:
    def generate_static_graph(self):
        if not settings.IMPLICATIONS_FILE.exists():
             logger.error("Implications file missing.")
             return

        with open(settings.IMPLICATIONS_FILE, 'r') as f:
            edges = json.load(f)
            
        G = nx.DiGraph()
        G.add_edges_from([(e['source'], e['target']) for e in edges])
        
        plt.figure(figsize=(12, 12))
        pos = nx.spring_layout(G, k=0.5, iterations=50)
        
        # Try graphviz if available
        try:
            from networkx.drawing.nx_agraph import graphviz_layout
            pos = graphviz_layout(G, prog='dot')
        except ImportError:
            pass
            
        nx.draw(G, pos, with_labels=True, node_size=1500, node_color='skyblue', 
                font_size=8, font_weight='bold', arrowsize=15, edge_color='gray')
        
        plt.title("Knowledge Structure (Implication Graph)")
        plt.savefig(settings.GRAPH_IMAGE_FILE)
        logger.info(f"Saved visualization to {settings.GRAPH_IMAGE_FILE}")

visualization_service = VisualizationService()
