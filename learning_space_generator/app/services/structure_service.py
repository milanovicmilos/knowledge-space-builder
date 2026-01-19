import pandas as pd
import numpy as np
import networkx as nx
import json
from learning_space_generator.app.core.config import settings
from learning_space_generator.app.services.semantic_service import semantic_service
import logging

logger = logging.getLogger(__name__)

class StructureService:
    def load_cleaned_data(self) -> pd.DataFrame:
        if not settings.CLEANED_DATA_FILE.exists():
            raise FileNotFoundError(f"{settings.CLEANED_DATA_FILE} not found. Run preprocessing first.")
        return pd.read_csv(settings.CLEANED_DATA_FILE)

    def extract_implications(self, data: pd.DataFrame, cluster_aware: bool = False) -> list[tuple]:
        items = data.columns.tolist()
        n_items = len(items)
        n_students = len(data)
        logger.info(f"Extracting implications from {n_students} students for {n_items} items (cluster_aware={cluster_aware}).")
        
        # --- Pre-calculate Semantic Similarity (ONLY for these specific items) ---
        logger.info("Computing Semantic Matrix for Regularization (subset)...")
        try:
            # Calculate semantic similarity ONLY for items in this data slice
            semantic_df = semantic_service.calculate_similarity_matrix(items)
            use_semantics = True
            # Only generate clusters on global run (not per-cluster)
            if not cluster_aware:
                semantic_service.generate_semantic_clusters(items)
        except Exception as e:
            logger.warning(f"Semantic analysis failed ({e}). Fallback to pure statistical IITA.")
            use_semantics = False

        X = data.values
        NotX = 1 - X
        # B[i, j] = count of (0, 1) pattern for i -> j
        B = np.dot(NotX.T, X)
        np.fill_diagonal(B, n_students) # Ignore self-loops

        base_threshold = n_students * settings.IITA_THRESHOLD_RATE
        logger.info(f"Base Threshold: {base_threshold} ({settings.IITA_THRESHOLD_RATE*100}%)")
        logger.info(f"Semantic Weight (Lambda): {settings.SEMANTIC_WEIGHT}")

        implications = []
        rejected_by_semantics = 0
        
        for i in range(n_items):
            for j in range(n_items):
                if i == j: continue
                
                b_xy = B[i, j]
                
                # Hybrid Scoring
                if use_semantics:
                    # adjusted_score = b_xy + lambda * (1 - Sim) * N
                    # Sim is between -1 and 1 usually, but here 0 to 1 mostly.
                    sim = semantic_df.iloc[i, j]
                    # Ensure sim is [0, 1]
                    sim = max(0, sim) 
                    
                    penalty = settings.SEMANTIC_WEIGHT * (1 - sim) * n_students
                    hybrid_score = b_xy + penalty
                else:
                    hybrid_score = b_xy

                if hybrid_score <= base_threshold:
                    implications.append((items[i], items[j]))
                else:
                    # Check if it WOULD have passed without penalty
                    if b_xy <= base_threshold and use_semantics:
                        rejected_by_semantics += 1

        logger.info(f"Found {len(implications)} raw implications.")
        if use_semantics:
            logger.info(f"Semantics filtered out {rejected_by_semantics} statistically potential links.")
            
        return implications

    def reduce_graph(self, items: list, implications: list[tuple]) -> list[tuple]:
        G = nx.DiGraph()
        G.add_nodes_from(items)
        G.add_edges_from(implications)

        if not nx.is_directed_acyclic_graph(G):
            logger.warning("Graph contains cycles. Removing heuristics...")
            while not nx.is_directed_acyclic_graph(G):
                try:
                    cycle = nx.find_cycle(G)
                    G.remove_edge(*cycle[-1])
                except nx.NetworkXNoCycle:
                    break

        logger.info("Performing transitive reduction...")
        TR = nx.transitive_reduction(G)
        reduced_edges = list(TR.edges())
        logger.info(f"Reduced to {len(reduced_edges)} essential edges.")
        return reduced_edges

    def save_implications(self, edges: list[tuple]):
        output_data = [{"source": u, "target": v} for u, v in edges]
        with open(settings.IMPLICATIONS_FILE, 'w') as f:
            json.dump(output_data, f, indent=2)
        logger.info(f"Saved implications to {settings.IMPLICATIONS_FILE}")

    def run_extraction(self):
        """
        Main IITA workflow: Load semantic clusters (if available), run IITA per-cluster + globally.
        """
        data = self.load_cleaned_data()
        
        # Try to load semantic clusters from Step 2
        clusters_file = settings.OUTPUT_DIR / "semantic_clusters.json"
        if clusters_file.exists():
            logger.info("Loading semantic clusters from previous step...")
            with open(clusters_file, 'r') as f:
                clusters = json.load(f)
            logger.info(f"Found {len(clusters)} semantic clusters.")
            
            # Run IITA per cluster (if cluster size >= min_threshold)
            min_cluster_size = 5
            all_cluster_implications = []
            
            for cluster_id, cluster_items in clusters.items():
                if len(cluster_items) < min_cluster_size:
                    logger.info(f"Cluster {cluster_id}: {len(cluster_items)} items (skipped, too small)")
                    continue
                
                logger.info(f"Running IITA for Cluster {cluster_id}: {len(cluster_items)} items")
                cluster_data = data[cluster_items]
                # IMPORTANT: Pass cluster_aware=True to only use semantic matrix for these items
                cluster_implications = self.extract_implications(cluster_data, cluster_aware=True)
                all_cluster_implications.extend(cluster_implications)
            
            logger.info(f"Total cluster-level implications: {len(all_cluster_implications)}")
            
            # Also run global IITA (optional: can merge or compare)
            logger.info("Running global IITA across all items (cluster_aware=False)...")
            global_implications = self.extract_implications(data, cluster_aware=False)
            
            # Merge: take union or intersection (here: union for now)
            combined = list(set(all_cluster_implications + global_implications))
            logger.info(f"Combined (cluster + global): {len(combined)} implications")
            
            reduced = self.reduce_graph(data.columns.tolist(), combined)
        else:
            logger.warning("No semantic clusters found; running global IITA only.")
            implications = self.extract_implications(data, cluster_aware=False)
            reduced = self.reduce_graph(data.columns.tolist(), implications)
        
        self.save_implications(reduced)

structure_service = StructureService()
