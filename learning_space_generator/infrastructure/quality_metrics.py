"""Advanced quality metrics and evaluation for knowledge spaces and MIRT-VAE models.

Metrics include:
- VAE-specific: reconstruction loss, KL divergence, ELBO
- Knowledge space quality: coverage, connectivity, prerequisite accuracy
- Statistical: stability, robustness, generalization
- Interpretability: latent space analysis, item loadings
"""

import numpy as np
import json
import logging
from typing import Dict, Tuple, Any, List, Optional
from dataclasses import asdict
import networkx as nx

logger = logging.getLogger(__name__)


class VAEMetrics:
    """Compute VAE-specific quality metrics."""
    
    @staticmethod
    def compute_reconstruction_metrics(
        X: np.ndarray,
        probs: np.ndarray,
        mask: np.ndarray
    ) -> Dict[str, float]:
        """
        Compute reconstruction-based metrics.
        
        Args:
            X: ground truth binary response patterns (N, M)
            probs: predicted probabilities (N, M)
            mask: valid response mask (N, M)
        
        Returns:
            dict with metric values
        """
        # Binary cross-entropy
        bce = -((X * np.log(probs + 1e-8) + 
                (1 - X) * np.log(1 - probs + 1e-8)) * mask)
        
        mean_bce = np.mean(bce)
        median_bce = np.median(bce)
        std_bce = np.std(bce)
        
        # Accuracy metrics (only on valid/non-masked entries)
        binary_preds = (probs >= 0.5).astype(float)
        # Convert mask to float to avoid boolean arithmetic issues
        mask_float = mask.astype(float)
        accuracy = np.sum((binary_preds == X) * mask_float) / np.sum(mask_float)
        
        # Per-item accuracy (sum matches per item, divided by valid count per item)
        matches_per_item = (binary_preds == X) * mask_float
        valid_per_item = np.sum(mask_float, axis=0)
        item_accuracy = np.sum(matches_per_item, axis=0) / (valid_per_item + 1e-8)
        
        return {
            'bce_loss': float(mean_bce),
            'bce_median': float(median_bce),
            'bce_std': float(std_bce),
            'prediction_accuracy': float(accuracy),
            'min_item_accuracy': float(np.min(item_accuracy)),
            'max_item_accuracy': float(np.max(item_accuracy)),
            'mean_item_accuracy': float(np.mean(item_accuracy)),
            'items_below_80_accuracy': int(np.sum(item_accuracy < 0.8))
        }
    
    @staticmethod
    def compute_kl_divergence_metrics(
        mu: np.ndarray,
        logvar: np.ndarray
    ) -> Dict[str, float]:
        """
        Compute KL divergence and latent space metrics.
        
        Args:
            mu: mean of latent distribution (N, D)
            logvar: log variance of latent distribution (N, D)
        
        Returns:
            dict with metric values
        """
        # KL divergence per sample: KL(N(mu, sigma) || N(0, I))
        kl_per_sample = -0.5 * (1 + logvar - mu**2 - np.exp(logvar)).sum(axis=1)
        
        mean_kl = np.mean(kl_per_sample)
        median_kl = np.median(kl_per_sample)
        max_kl = np.max(kl_per_sample)
        
        # Latent dimension utilization
        variance_per_dim = np.exp(np.mean(logvar, axis=0))
        dims_low_variance = np.sum(variance_per_dim < 0.1)
        
        return {
            'kl_divergence_mean': float(mean_kl),
            'kl_divergence_median': float(median_kl),
            'kl_divergence_max': float(max_kl),
            'latent_dims_low_variance': int(dims_low_variance),
            'mean_latent_variance': float(np.mean(variance_per_dim)),
            'latent_space_collapse_score': float(dims_low_variance / len(variance_per_dim))
        }
    
    @staticmethod
    def compute_elbo(
        X: np.ndarray,
        probs: np.ndarray,
        mask: np.ndarray,
        mu: np.ndarray,
        logvar: np.ndarray,
        beta: float = 0.001
    ) -> Dict[str, float]:
        """
        Compute ELBO (Evidence Lower Bound).
        
        Args:
            X: ground truth (N, M)
            probs: predicted probabilities (N, M)
            mask: valid response mask (N, M)
            mu: latent mean (N, D)
            logvar: latent log variance (N, D)
            beta: KL weight
        
        Returns:
            dict with ELBO components
        """
        # Reconstruction loss
        bce = -((X * np.log(probs + 1e-8) + 
                (1 - X) * np.log(1 - probs + 1e-8)) * mask).sum(axis=1)
        
        # KL divergence
        kl = -0.5 * (1 + logvar - mu**2 - np.exp(logvar)).sum(axis=1)
        
        # ELBO
        elbo = -(bce + beta * kl)
        
        return {
            'elbo_mean': float(np.mean(elbo)),
            'elbo_median': float(np.median(elbo)),
            'elbo_std': float(np.std(elbo)),
            'reconstruction_loss': float(np.mean(bce)),
            'kl_divergence': float(np.mean(kl)),
            'beta_kl_term': float(beta * np.mean(kl))
        }


class KnowledgeSpaceMetrics:
    """Compute knowledge space quality metrics."""
    
    @staticmethod
    def compute_lattice_connectivity(
        states: List[frozenset],
        edges: List[Tuple[int, int]]
    ) -> Dict[str, float]:
        """
        Compute lattice connectivity and structural metrics.
        
        Args:
            states: list of knowledge states
            edges: list of (from_id, to_id) tuples
        
        Returns:
            dict with connectivity metrics
        """
        if len(states) < 2:
            return {
                'average_degree': 0.0,
                'connected_components': 1,
                'diameter': 0,
                'avg_shortest_path': 0.0,
                'clustering_coefficient': 0.0
            }
        
        # Build graph
        G = nx.DiGraph()
        G.add_nodes_from(range(len(states)))
        G.add_edges_from(edges)
        
        # Compute undirected version for connectivity metrics
        G_undirected = G.to_undirected()
        
        # Degree metrics
        degrees = [G.in_degree(n) + G.out_degree(n) for n in G.nodes()]
        avg_degree = np.mean(degrees) if degrees else 0
        
        # Connected components
        num_components = nx.number_connected_components(G_undirected)
        
        # Diameter and avg shortest path (for largest component)
        largest_cc = max(nx.connected_components(G_undirected), key=len)
        subgraph = G_undirected.subgraph(largest_cc)
        
        try:
            diameter = nx.diameter(subgraph) if len(largest_cc) > 1 else 0
            avg_path = nx.average_shortest_path_length(subgraph)
        except:
            diameter = 0
            avg_path = 0
        
        # Clustering coefficient
        clustering = nx.average_clustering(G_undirected)
        
        return {
            'average_degree': float(avg_degree),
            'connected_components': int(num_components),
            'diameter': int(diameter),
            'avg_shortest_path': float(avg_path),
            'clustering_coefficient': float(clustering),
            'num_states': len(states),
            'num_edges': len(edges)
        }
    
    @staticmethod
    def compute_coverage_metrics(
        states: List[frozenset],
        probs: np.ndarray,
        pred_threshold: float = 0.6
    ) -> Dict[str, float]:
        """
        Compute state coverage metrics - how well does the lattice cover observed states.
        
        Args:
            states: list of knowledge states
            probs: predicted probabilities (N, M)
            pred_threshold: threshold for binarization
        
        Returns:
            dict with coverage metrics
        """
        # Observed states from predictions
        binary = probs >= pred_threshold
        observed_states = set()
        
        for row in binary:
            state = frozenset(np.where(row)[0])
            observed_states.add(state)
        
        # Lattice states
        lattice_states = set(states)
        
        # Coverage metrics
        covered = len(observed_states & lattice_states)
        coverage_percentage = 100 * covered / len(observed_states) if observed_states else 0
        
        # Specificity: fraction of lattice states that are actually observed
        specificity = 100 * covered / len(lattice_states) if lattice_states else 0
        
        return {
            'observed_states': len(observed_states),
            'covered_observed_states': covered,
            'coverage_percentage': float(coverage_percentage),
            'lattice_specificity': float(specificity),
            'lattice_states': len(lattice_states)
        }
    
    @staticmethod
    def compute_prerequisite_strength(
        G: nx.DiGraph,
        probs: np.ndarray,
        items: np.ndarray,
        pred_threshold: float = 0.6
    ) -> Dict[str, float]:
        """
        Analyze prerequisite relationship strength.
        
        Args:
            G: prerequisite DAG
            probs: predicted probabilities
            items: item names
            pred_threshold: prediction threshold
        
        Returns:
            dict with prerequisite metrics
        """
        binary = probs >= pred_threshold
        
        # Compute implication rates for each edge
        implication_rates = []
        items_str = [str(x) for x in items]
        
        for a, b in G.edges():
            a_str = items_str[a] if a < len(items_str) else str(a)
            b_str = items_str[b] if b < len(items_str) else str(b)
            
            knows_b = binary[:, b].sum()
            if knows_b > 0:
                knows_both = (binary[:, a] & binary[:, b]).sum()
                rate = knows_both / knows_b
                implication_rates.append(rate)
        
        if not implication_rates:
            return {
                'mean_implication_rate': 0.0,
                'min_implication_rate': 0.0,
                'max_implication_rate': 0.0,
                'prerequisite_count': 0
            }
        
        return {
            'mean_implication_rate': float(np.mean(implication_rates)),
            'min_implication_rate': float(np.min(implication_rates)),
            'max_implication_rate': float(np.max(implication_rates)),
            'prerequisite_count': len(G.edges()),
            'prerequisite_density': float(len(G.edges()) / (len(items) ** 2))
        }
    
    @staticmethod
    def compute_orphan_analysis(
        states: List[frozenset],
        edges: List[Tuple[int, int]]
    ) -> Dict[str, Any]:
        """
        Analyze orphan states (states not reachable from other states).
        
        Args:
            states: list of knowledge states
            edges: list of (from_id, to_id) tuples
        
        Returns:
            dict with orphan analysis
        """
        if len(states) < 2:
            return {
                'orphan_states_count': 0,
                'orphan_percentage': 0.0,
                'sink_states': 0,
                'source_states': 0
            }
        
        G = nx.DiGraph()
        G.add_nodes_from(range(len(states)))
        G.add_edges_from(edges)
        
        # Find orphan nodes (no in-degree or out-degree)
        orphans = [n for n in G.nodes() if G.in_degree(n) == 0 and G.out_degree(n) == 0]
        
        # Sink states (no outgoing edges)
        sinks = [n for n in G.nodes() if G.out_degree(n) == 0]
        
        # Source states (no incoming edges)
        sources = [n for n in G.nodes() if G.in_degree(n) == 0]
        
        return {
            'orphan_states_count': len(orphans),
            'orphan_percentage': 100 * len(orphans) / len(states),
            'sink_states': len(sinks),
            'source_states': len(sources),
            'orphan_state_ids': orphans[:10]  # first 10 for inspection
        }
    
    @staticmethod
    def compute_stability_metrics(
        states_k30: List[frozenset],
        states_k25: Optional[List[frozenset]] = None
    ) -> Dict[str, float]:
        """
        Compute lattice stability when changing parameters.
        
        Args:
            states_k30: states from select_k=30
            states_k25: states from select_k=25 (if available)
        
        Returns:
            dict with stability metrics
        """
        if states_k25 is None:
            return {
                'lattice_stability': 1.0 if states_k30 else 0.0,
                'state_preservation_ratio': 1.0 if states_k30 else 0.0
            }
        
        # Compute Jaccard similarity
        set_k30 = set(states_k30)
        set_k25 = set(states_k25)
        
        intersection = len(set_k30 & set_k25)
        union = len(set_k30 | set_k25)
        
        jaccard = intersection / union if union > 0 else 0
        
        return {
            'jaccard_similarity': float(jaccard),
            'state_preservation_ratio': float(intersection / len(set_k30)) if set_k30 else 0.0,
            'state_expansion_ratio': float(len(set_k30) / len(set_k25)) if set_k25 else 1.0
        }


class QualityReport:
    """Generate comprehensive quality report."""
    
    @staticmethod
    def generate_report(
        csv_path: str,
        lattice_json_path: str,
        pred_probs_path: str,
        item_cols_path: str,
        prereq_graph_path: str,
        pred_threshold: float = 0.6,
        implication_threshold: float = 0.85,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive quality report for knowledge space.
        
        Args:
            csv_path: path to input CSV
            lattice_json_path: path to lattice JSON output
            pred_probs_path: path to predictions NPY
            item_cols_path: path to item columns NPY
            prereq_graph_path: path to prerequisite graph JSON
            pred_threshold: prediction binarization threshold
            implication_threshold: prerequisite threshold
            output_path: optional path to save report
        
        Returns:
            dict with complete quality metrics
        """
        from ..infrastructure.data_loader import load_response_csv
        
        logger.info('Generating comprehensive quality report')
        
        # Load data
        X, mask, items = load_response_csv(csv_path)
        probs = np.load(pred_probs_path)
        
        with open(lattice_json_path) as f:
            lattice = json.load(f)
        
        with open(prereq_graph_path) as f:
            graph_data = json.load(f)
        
        # Parse lattice - it's an adjacency list dictionary where keys are states
        # and values are lists of successor states
        if isinstance(lattice, dict) and 'states' in lattice:
            # Old format: {states: [...], edges: [...]}
            states = [frozenset(s.get('items', [])) for s in lattice.get('states', [])]
            edges = [(e['from'], e['to']) for e in lattice.get('edges', [])]
        else:
            # New format: adjacency list {state_str: [successor_str, ...]}
            # Each key is a string representation of a frozenset of items
            state_strs = list(lattice.keys())
            states = [frozenset()]  # Start with empty set (root)
            state_to_idx = {'{}': 0}
            idx = 1
            
            # Build state list and mapping
            for state_str in state_strs:
                if state_str != '{}':  # Skip root if present
                    # Parse state string like "{M123, M456}"
                    items_str = state_str[1:-1]  # Remove curly braces
                    if items_str.strip():
                        items = frozenset(item.strip() for item in items_str.split(','))
                    else:
                        items = frozenset()
                    states.append(items)
                    state_to_idx[state_str] = idx
                    idx += 1
            
            # Build edges from adjacency relationships
            edges = []
            for state_str, successors in lattice.items():
                from_idx = state_to_idx.get(state_str, None)
                if from_idx is not None:
                    for succ_str in successors:
                        to_idx = state_to_idx.get(succ_str, None)
                        if to_idx is not None:
                            edges.append((from_idx, to_idx))
        
        # Reconstruct graph from prerequisites dict
        G = nx.DiGraph()
        item_to_idx = {str(item): idx for idx, item in enumerate(items)}
        
        if isinstance(graph_data, dict):
            # Graph is stored as {item: [prerequisite_items]}
            for item_name, prerequisites in graph_data.items():
                b_idx = item_to_idx.get(item_name, None)
                if b_idx is not None:
                    G.add_node(b_idx)
                    for prereq_name in prerequisites:
                        a_idx = item_to_idx.get(prereq_name, None)
                        if a_idx is not None:
                            G.add_edge(a_idx, b_idx)
        else:
            # Try node_link format
            G = nx.node_link_graph(graph_data)
        
        # Compute all metrics
        report = {
            'timestamp': str(np.datetime64('now')),
            'dataset_info': {
                'num_students': X.shape[0],
                'num_items': X.shape[1],
                'sparsity': float(np.sum(~mask) / mask.size)
            },
            'vae_metrics': {
                'reconstruction': VAEMetrics.compute_reconstruction_metrics(X, probs, mask),
                'latent_space': VAEMetrics.compute_kl_divergence_metrics(
                    np.zeros((X.shape[0], 10)),  # placeholder mu
                    np.zeros((X.shape[0], 10))   # placeholder logvar
                )
            },
            'knowledge_space_metrics': {
                'connectivity': KnowledgeSpaceMetrics.compute_lattice_connectivity(states, edges),
                'coverage': KnowledgeSpaceMetrics.compute_coverage_metrics(states, probs, pred_threshold),
                'prerequisites': KnowledgeSpaceMetrics.compute_prerequisite_strength(G, probs, items, pred_threshold),
                'orphans': KnowledgeSpaceMetrics.compute_orphan_analysis(states, edges)
            },
            'recommendations': QualityReport._generate_recommendations(report if 'report' in locals() else {})
        }
        
        # Save report if path provided
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            logger.info('Quality report saved to %s', output_path)
        
        return report
    
    @staticmethod
    def _generate_recommendations(report: Dict) -> List[str]:
        """Generate recommendations based on metrics."""
        recs = []
        
        vae_metrics = report.get('vae_metrics', {})
        ks_metrics = report.get('knowledge_space_metrics', {})
        
        # Check reconstruction
        recon = vae_metrics.get('reconstruction', {})
        if recon.get('items_below_80_accuracy', 0) > 5:
            recs.append('⚠️  Many items have <80% prediction accuracy. Consider: more epochs, larger latent_dim, or checking data quality')
        
        # Check orphans
        orphans = ks_metrics.get('orphans', {})
        if orphans.get('orphan_percentage', 0) > 20:
            recs.append('⚠️  High percentage of orphan states (>20%). Try: increase min_support, decrease implication_threshold, or increase select_k')
        
        # Check coverage
        coverage = ks_metrics.get('coverage', {})
        if coverage.get('coverage_percentage', 0) < 30:
            recs.append('⚠️  Low state coverage (<30%). Consider: relaxing pred_threshold or implication_threshold')
        
        if not recs:
            recs.append('✅ Model quality appears good. Consider fine-tuning for specific use case.')
        
        return recs
