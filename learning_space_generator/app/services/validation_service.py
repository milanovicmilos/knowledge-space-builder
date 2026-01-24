import json
import networkx as nx
from pypdf import PdfReader
from learning_space_generator.app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class ValidationService:
    def validate_structure(self):
        if not settings.IMPLICATIONS_FILE.exists():
            logger.error("Implications file missing.")
            return

        with open(settings.IMPLICATIONS_FILE, 'r') as f:
            edges = json.load(f)
            
        G = nx.DiGraph()
        G.add_edges_from([(e['source'], e['target']) for e in edges])
        
        logger.info(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges.")
        logger.info(f"Density: {nx.density(G):.4f}")
        
        # Determine components
        components = list(nx.weakly_connected_components(G))
        logger.info(f"Weakly Connected Components: {len(components)}")
        logger.info(f"Sizes: {[len(c) for c in components]}")

    def semantic_validation_check(self):
        if not settings.PDF_FILE.exists():
            logger.warning(f"PDF file {settings.PDF_FILE} not found. Skipping semantic check.")
            return

        logger.info(f"Extracting text from {settings.PDF_FILE}...")
        try:
            reader = PdfReader(settings.PDF_FILE)
            full_text = ""
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
        except Exception as e:
            logger.error(f"Failed to read PDF: {e}")
            return

        # Simple validation: Check if nodes exist in text
        # Loading nodes from cleaned data to be sure
        if settings.CLEANED_DATA_FILE.exists():
            import pandas as pd
            df = pd.read_csv(settings.CLEANED_DATA_FILE)
            nodes = df.columns.tolist()
        else:
            return

        found = 0
        for node in nodes:
            # Heuristic for matching code in PDF
            # e.g. s1m11a091 -> m11a091
            if node.startswith('s1') or node.startswith('s2'):
                search_term = node[2:]
            else:
                search_term = node
                
            if search_term in full_text:
                found += 1
                
        logger.info(f"Found descriptions for {found} out of {len(nodes)} items in PDF.")

validation_service = ValidationService()
