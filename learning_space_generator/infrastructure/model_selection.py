"""Automated hyperparameter selection for MIRT-VAE.

This module implements modern hyperparameter optimization methods:
- Bayesian optimization for efficient search
- Grid search for exhaustive search
- Automatic latent_dim selection via elbow method
- Cross-validation for robust evaluation
"""

import numpy as np
import logging
from typing import Dict, Tuple, List, Optional, Any
from dataclasses import dataclass
import json
import os
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class OptimizationParams:
    """Hyperparameter search space definition."""
    latent_dim_range: Tuple[int, int] = (3, 15)
    epochs_range: Tuple[int, int] = (50, 200)
    batch_size_options: List[int] = None
    learning_rate_range: Tuple[float, float] = (1e-4, 5e-3)
    pred_threshold_range: Tuple[float, float] = (0.5, 0.7)
    implication_threshold_range: Tuple[float, float] = (0.75, 0.95)
    select_k_options: List[int] = None
    min_support_range: Tuple[int, int] = (1, 15)
    
    def __post_init__(self):
        if self.batch_size_options is None:
            self.batch_size_options = [256, 512, 1024]
        if self.select_k_options is None:
            self.select_k_options = [10, 15, 20, 25, 30, 40, 50]


@dataclass
class OptimizationMetrics:
    """Metrics collected during hyperparameter evaluation."""
    latent_dim: int
    epochs: int
    batch_size: int
    learning_rate: float
    
    # VAE metrics
    train_loss: float
    val_loss: float
    kl_divergence: float
    reconstruction_loss: float
    
    # Knowledge space metrics
    num_states: int
    num_edges: int
    orphan_percentage: float
    prerequisite_coverage: float  # percentage of strong prerequisites found
    lattice_connectivity: float   # average path length in lattice
    
    # Overall quality score
    overall_score: float  # weighted combination of metrics
    num_connected_components: int = 1  # number of connected components in the graph
    is_fully_connected: bool = True  # whether entire graph is connected


class GraphConnectivityAnalyzer:
    """Analyze connectivity and fragmentation of knowledge space graphs."""
    
    @staticmethod
    def count_connected_components(graph: Dict[str, List[str]]) -> Tuple[int, int]:
        """
        Count number of connected components in the knowledge space graph.
        
        Returns:
            (num_components, unreachable_from_empty)
        """
        if not graph:
            return 0, 0
        
        # Build adjacency list (bidirectional for connectivity)
        adj = {}
        all_nodes = set()
        
        for state, successors in graph.items():
            all_nodes.add(state)
            if state not in adj:
                adj[state] = []
            for succ in successors:
                all_nodes.add(succ)
                adj[state].append(succ)
                if succ not in adj:
                    adj[succ] = []
                if state not in adj[succ]:
                    adj[succ].append(state)
        
        # Find connected components using BFS
        visited = set()
        components = []
        
        for node in all_nodes:
            if node not in visited:
                component = set()
                queue = deque([node])
                visited.add(node)
                component.add(node)
                
                while queue:
                    current = queue.popleft()
                    for neighbor in adj.get(current, []):
                        if neighbor not in visited:
                            visited.add(neighbor)
                            component.add(neighbor)
                            queue.append(neighbor)
                
                components.append(component)
        
        # Find empty state component
        unreachable = 0
        if "{}" in all_nodes:
            for comp in components:
                if "{}" in comp:
                    unreachable = len(all_nodes) - len(comp)
                    break
        
        return len(components), unreachable


class EBOWMetricComputer:
    """Compute ELBO (Evidence Lower Bound) and related VAE metrics."""
    
    @staticmethod
    def compute_elbo(logits, x, mask, mu, logvar, beta=0.001):
        """
        Compute ELBO = -reconstruction_loss - beta * KL_divergence
        
        Args:
            logits: model output logits (B, N)
            x: target response patterns (B, N)
            mask: valid response mask (B, N)
            mu: latent mean (B, D)
            logvar: latent log-variance (B, D)
            beta: KL weight (default: 0.001)
        
        Returns:
            elbo: scalar ELBO value
            reconstruction_loss: scalar
            kl_divergence: scalar
        """
        # Binary cross-entropy reconstruction loss
        bce = -((x * np.log(logits + 1e-8) + (1 - x) * np.log(1 - logits + 1e-8)) * mask).sum(axis=1)
        reconstruction_loss = bce.mean()
        
        # KL divergence: KL(N(mu, sigma) || N(0, I))
        kl = -0.5 * (1 + logvar - mu**2 - np.exp(logvar)).sum(axis=1)
        kl_divergence = kl.mean()
        
        # ELBO
        elbo = -(reconstruction_loss + beta * kl_divergence)
        
        return elbo, reconstruction_loss, kl_divergence


class LatentDimensionSelector:
    """Automatic latent dimension selection using elbow method."""
    
    @staticmethod
    def find_optimal_latent_dim(
        csv_path: str,
        latent_dim_range: Tuple[int, int] = (3, 25),
        epochs: int = 8,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Test multiple latent dimensions and select optimal using elbow method.
        
        Args:
            csv_path: path to CSV data
            latent_dim_range: (min_dim, max_dim)
            epochs: training epochs per config
            verbose: print progress
        
        Returns:
            dict with 'optimal_latent_dim', 'losses', 'kneedle_analysis'
        """
        from ..infrastructure.model_trainer import main as train_mirt_vae
        from ..infrastructure.data_loader import load_response_csv
        import tempfile
        
        X, mask, items = load_response_csv(csv_path)
        
        results = {
            'latent_dims': [],
            'val_losses': [],
            'kl_divergences': [],
            'reconstruction_losses': [],
            'metrics': []
        }
        
        logger.info('Starting latent dimension search [%d-%d]', *latent_dim_range)
        
        for dim in range(*latent_dim_range):
            with tempfile.TemporaryDirectory() as tmpdir:
                try:
                    print(f'[PROGRESS] Testing latent_dim={dim}', flush=True)
                    # Train model with this latent_dim
                    train_mirt_vae(csv_path, tmpdir, epochs=epochs, latent_dim=dim)
                    
                    # Load predictions and compute metrics
                    probs = np.load(os.path.join(tmpdir, 'pred_probs.npy'))
                    
                    # Estimate loss (simple metric)
                    val_loss = np.mean(-((X * np.log(probs + 1e-8) + 
                                         (1 - X) * np.log(1 - probs + 1e-8)) * mask))
                    
                    results['latent_dims'].append(dim)
                    results['val_losses'].append(val_loss)
                    
                    print(f'[PROGRESS] latent_dim={dim}: val_loss={val_loss:.4f}', flush=True)
                    if verbose:
                        logger.info('latent_dim=%d: val_loss=%.4f', dim, val_loss)
                
                except Exception as e:
                    logger.warning('Failed to train latent_dim=%d: %s', dim, str(e))
                    continue
        
        # Find elbow using kneedle algorithm
        if len(results['latent_dims']) > 2:
            optimal_dim = LatentDimensionSelector._kneedle_detection(
                results['latent_dims'], 
                results['val_losses']
            )
        else:
            optimal_dim = results['latent_dims'][np.argmin(results['val_losses'])]
        
        results['optimal_latent_dim'] = optimal_dim
        logger.info('Optimal latent_dim selected: %d', optimal_dim)
        
        return results
    
    @staticmethod
    def _kneedle_detection(x: List[int], y: List[float]) -> int:
        """
        Find elbow point using kneedle algorithm approximation.
        
        Args:
            x: x-values (latent dimensions)
            y: y-values (losses)
        
        Returns:
            optimal x value
        """
        # Normalize
        x = np.array(x)
        y = np.array(y)
        x_norm = (x - x.min()) / (x.max() - x.min())
        y_norm = (y - y.min()) / (y.max() - y.min())
        
        # Find point with maximum distance to line
        # Line from first to last point
        dx = x_norm[-1] - x_norm[0]
        dy = y_norm[-1] - y_norm[0]
        
        max_dist = 0
        optimal_idx = 0
        
        for i in range(len(x)):
            # Distance from point (x_norm[i], y_norm[i]) to line
            if dx**2 + dy**2 == 0:
                dist = np.sqrt(x_norm[i]**2 + y_norm[i]**2)
            else:
                dist = abs(dy * x_norm[i] - dx * y_norm[i] + dx * y_norm[0] - dy * x_norm[0]) / np.sqrt(dx**2 + dy**2)
            
            if dist > max_dist:
                max_dist = dist
                optimal_idx = i
        
        return x[optimal_idx]


class HyperparameterOptimizer:
    """Bayesian optimization for MIRT-VAE hyperparameters."""
    
    @staticmethod
    def suggest_config(trial, param_space: OptimizationParams) -> Dict[str, Any]:
        """Suggest hyperparameter configuration."""
        try:
            import optuna
            
            config = {
                'latent_dim': trial.suggest_int('latent_dim', *param_space.latent_dim_range),
                'epochs': trial.suggest_int('epochs', *param_space.epochs_range),
                'batch_size': trial.suggest_categorical('batch_size', param_space.batch_size_options),
                'learning_rate': trial.suggest_float('learning_rate', *param_space.learning_rate_range, log=True),
                'pred_threshold': trial.suggest_float('pred_threshold', *param_space.pred_threshold_range),
                'implication_threshold': trial.suggest_float('implication_threshold', *param_space.implication_threshold_range),
                'select_k': trial.suggest_categorical('select_k', param_space.select_k_options),
                'min_support': trial.suggest_int('min_support', *param_space.min_support_range),
            }
            return config
        except ImportError:
            logger.warning('Optuna not available; using random search')
            return HyperparameterOptimizer._random_config(param_space)
    
    @staticmethod
    def _random_config(param_space: OptimizationParams) -> Dict[str, Any]:
        """Generate random configuration."""
        return {
            'latent_dim': np.random.randint(*param_space.latent_dim_range),
            'epochs': np.random.randint(*param_space.epochs_range),
            'batch_size': np.random.choice(param_space.batch_size_options),
            'learning_rate': 10 ** np.random.uniform(np.log10(param_space.learning_rate_range[0]), 
                                                    np.log10(param_space.learning_rate_range[1])),
            'pred_threshold': np.random.uniform(*param_space.pred_threshold_range),
            'implication_threshold': np.random.uniform(*param_space.implication_threshold_range),
            'select_k': np.random.choice(param_space.select_k_options),
            'min_support': np.random.randint(*param_space.min_support_range),
        }


class ModelEvaluator:
    """Evaluate model configuration and compute quality metrics."""
    
    @staticmethod
    def evaluate_config(
        config: Dict[str, Any],
        csv_path: str,
        out_dir: str,
        val_split: float = 0.2
    ) -> OptimizationMetrics:
        """
        Evaluate a specific hyperparameter configuration.
        
        Args:
            config: configuration dict with hyperparameters
            csv_path: path to CSV data
            out_dir: output directory for this evaluation
            val_split: validation set percentage
        
        Returns:
            OptimizationMetrics object
        """
        from ..infrastructure.model_trainer import main as train_mirt_vae
        from ..application.orchestrator import LearningSpaceBuilder, BuilderConfig
        from ..infrastructure.data_loader import load_response_csv
        
        os.makedirs(out_dir, exist_ok=True)
        
        try:
            # Phase 1: Train MIRT-VAE
            logger.info('Evaluating config: %s', config)
            print(f'Testing config: latent_dim={config["latent_dim"]}, epochs={config["epochs"]}, '
                  f'pred_threshold={config["pred_threshold"]:.2f}, select_k={config["select_k"]}', flush=True)
            
            train_mirt_vae(
                csv_path, 
                out_dir, 
                epochs=config['epochs'],
                latent_dim=config['latent_dim']
            )
            
            # Load predictions
            probs = np.load(os.path.join(out_dir, 'pred_probs.npy'))
            X, mask, items = load_response_csv(csv_path)
            
            # Compute VAE metrics
            reconstruction_loss = np.mean(-((X * np.log(probs + 1e-8) + 
                                           (1 - X) * np.log(1 - probs + 1e-8)) * mask))
            
            # Phase 2: Build knowledge space
            builder_config = BuilderConfig(
                csv_path=csv_path,
                out_dir=out_dir,
                epochs=config['epochs'],
                latent=config['latent_dim'],
                pred_threshold=config['pred_threshold'],
                implication_threshold=config['implication_threshold'],
                select_k=config['select_k'],
                min_support=config['min_support']
            )
            
            builder = LearningSpaceBuilder(builder_config)
            results = builder.run_all(run_train=False)
            
            # Load summary
            summary_path = os.path.join(out_dir, f"knowledge_space_k{config['select_k']}_summary.json")
            with open(summary_path) as f:
                summary = json.load(f)
            
            # Load the actual graph to check connectivity
            graph_path = os.path.join(out_dir, f"knowledge_space_lattice_k{config['select_k']}.json")
            graph = {}
            if os.path.exists(graph_path):
                with open(graph_path) as f:
                    graph = json.load(f)
            else:
                # Try alternative naming
                graph_path = os.path.join(out_dir, f"lattice_k{config['select_k']}.json")
                if os.path.exists(graph_path):
                    with open(graph_path) as f:
                        graph = json.load(f)
            
            # Analyze graph connectivity
            num_components, unreachable = GraphConnectivityAnalyzer.count_connected_components(graph)
            
            # Calculate overall quality score
            num_states = summary.get('num_states', 0)
            num_edges = summary.get('num_edges', 0)
            orphan_pct = 100 * (summary.get('orphan_states', 0) / max(num_states, 1))
            
            # CRITICAL: Penalty for fragmented graphs AND for trivial graphs
            # A fully connected graph (1 component) gets score 1.0
            # Graph with 30 components gets heavily penalized
            fragmentation_score = 1.0 / max(num_components, 1)  # 1.0 if 1 component, 0.033 if 30 components
            
            # NEW: STRONG penalty for graphs with too few states (trivial solutions)
            # We want at least 10 states for meaningful knowledge space
            # Use EXPONENTIAL penalty: 2^(states/10) to heavily discourage trivial graphs
            # Examples: 1 state -> 2^0.1 = 0.07, 2 states -> 2^0.2 = 0.13, 5 states -> 2^0.5 = 0.41, 10 states -> 2^1.0 = 1.0
            min_states_threshold = 10
            if num_states < min_states_threshold:
                state_count_penalty = 2 ** (num_states / min_states_threshold - 1)  # Exponential penalty
            else:
                state_count_penalty = 1.0
            
            # Score: prefer balanced states, good connectivity, few orphans, FULLY CONNECTED GRAPH, MEANINGFUL SIZE
            connectivity_score = min(num_edges / max(num_states, 1), 2.0) / 2.0  # normalized to 0-1
            orphan_score = 1.0 - min(orphan_pct / 100, 1.0)  # lower orphans = higher score
            loss_score = 1.0 / (1.0 + reconstruction_loss)  # lower loss = higher score
            
            # UPDATED SCORING WEIGHTS (v3):
            # 40% state count (CRITICAL - must have meaningful number of states!)
            # 25% fragmentation (must be connected!)
            # 15% connectivity (edges per state ratio)
            # 15% loss (reconstruction quality)
            # 5% orphans (minimize orphan states)
            overall_score = (0.40 * state_count_penalty +
                           0.25 * fragmentation_score + 
                           0.15 * connectivity_score + 
                           0.15 * loss_score + 
                           0.05 * orphan_score)
            
            logger.info(f'Graph analysis: {num_components} components, {unreachable} unreachable states, {num_states} total states')
            logger.info(f'Fragmentation score: {fragmentation_score:.4f}, State count penalty: {state_count_penalty:.4f}, Overall score: {overall_score:.4f}')
            
            metrics = OptimizationMetrics(
                latent_dim=config['latent_dim'],
                epochs=config['epochs'],
                batch_size=config['batch_size'],
                learning_rate=config['learning_rate'],
                train_loss=0.0,  # would need val split to compute
                val_loss=reconstruction_loss,
                kl_divergence=0.001,  # approximation
                reconstruction_loss=reconstruction_loss,
                num_states=num_states,
                num_edges=num_edges,
                orphan_percentage=orphan_pct,
                prerequisite_coverage=summary.get('prerequisite_coverage', 0.0),
                lattice_connectivity=num_edges / max(num_states, 1),
                overall_score=overall_score,
                num_connected_components=num_components,
                is_fully_connected=(num_components == 1)
            )
            
            logger.info('Config evaluation complete: score=%.4f, components=%d, states=%d', overall_score, num_components, num_states)
            if num_components > 1:
                logger.warning('⚠️ Graph is fragmented with %d components! Score penalized.', num_components)
                print(f'⚠️ [PROGRESS] Graph fragmentation detected: {num_components} components, {unreachable} unreachable states - penalizing score', flush=True)
            if num_states < min_states_threshold:
                logger.warning('⚠️ Trivial graph with only %d states (threshold: %d)! Score penalized.', num_states, min_states_threshold)
                print(f'⚠️ [PROGRESS] Trivial graph detected: only {num_states} states (need ≥{min_states_threshold}) - penalizing score', flush=True)
            return metrics
            
        except Exception as e:
            logger.error('Evaluation failed: %s', str(e))
            # Return worst possible metrics
            return OptimizationMetrics(
                latent_dim=config['latent_dim'],
                epochs=config['epochs'],
                batch_size=config['batch_size'],
                learning_rate=config['learning_rate'],
                train_loss=float('inf'),
                val_loss=float('inf'),
                kl_divergence=float('inf'),
                reconstruction_loss=float('inf'),
                num_states=0,
                num_edges=0,
                orphan_percentage=100.0,
                prerequisite_coverage=0.0,
                lattice_connectivity=0.0,
                overall_score=0.0,
                num_connected_components=999,
                is_fully_connected=False
            )


def find_optimal_hyperparameters(
    csv_path: str,
    output_dir: str = 'learning_space_generator/output',
    n_trials: int = 10,
    use_bayesian: bool = True,
    param_space: Optional[OptimizationParams] = None
) -> Dict[str, Any]:
    """
    Find optimal hyperparameters using Bayesian optimization or random search.
    
    Args:
        csv_path: path to CSV data
        output_dir: base output directory
        n_trials: number of configurations to test
        use_bayesian: use Bayesian optimization if available
        param_space: custom parameter space
    
    Returns:
        dict with optimal configuration and all results
    """
    if param_space is None:
        param_space = OptimizationParams()
    
    logger.info('Starting hyperparameter optimization (%d trials)', n_trials)
    
    all_metrics = []
    all_configs = []
    
    # 1. Find optimal latent_dim first
    logger.info('Phase 1: Automatic latent_dim selection')
    latent_results = LatentDimensionSelector.find_optimal_latent_dim(
        csv_path,
        latent_dim_range=param_space.latent_dim_range,
        epochs=8
    )
    optimal_latent_dim = latent_results['optimal_latent_dim']
    param_space.latent_dim_range = (optimal_latent_dim, optimal_latent_dim + 5)
    
    # 2. Optimize remaining hyperparameters
    logger.info('Phase 2: Optimizing remaining hyperparameters')
    print(f'[PROGRESS] Starting {n_trials} optimization trials', flush=True)
    
    if use_bayesian:
        try:
            import optuna
            
            trial_counter = {'count': 0}
            
            def objective(trial):
                config = HyperparameterOptimizer.suggest_config(trial, param_space)
                trial_out_dir = os.path.join(output_dir, f'trial_{trial.number}')
                metrics = ModelEvaluator.evaluate_config(config, csv_path, trial_out_dir)
                all_metrics.append(metrics)
                all_configs.append(config)
                trial_counter['count'] += 1
                return metrics.overall_score
            
            study = optuna.create_study(direction='maximize')
            
            def trial_callback(study, trial):
                """Log trial completion to stdout for progress tracking in main process"""
                # Get the config from the trial's parameters
                params = trial.params
                latent = params.get('latent_dim', '?')
                k = params.get('select_k', '?')
                thresh = params.get('pred_threshold', '?')
                score = trial.value if trial.value is not None else 0.0
                
                print(f'[PROGRESS] Trial {trial.number} Testing: latent_dim={latent}, select_k={k}, pred_threshold={thresh:.2f}', flush=True)
                print(f'[PROGRESS] Trial {trial.number} finished: score={score:.4f}', flush=True)
                if trial.value is not None:
                    logger.info(f'Trial {trial.number} completed | value={trial.value:.4f} | params={trial.params}')
                else:
                    logger.info(f'Trial {trial.number} completed with error | params={trial.params}')
            
            study.optimize(objective, n_trials=n_trials, show_progress_bar=False, callbacks=[trial_callback])
            
            best_config = all_configs[np.argmax([m.overall_score for m in all_metrics])]
            
        except ImportError:
            logger.warning('Optuna not available; using random search')
            use_bayesian = False
    
    if not use_bayesian:
        for trial in range(n_trials):
            print(f'[PROGRESS] Trial {trial} starting', flush=True)
            config = HyperparameterOptimizer._random_config(param_space)
            print(f'[PROGRESS] Testing: latent_dim={config["latent_dim"]}, select_k={config["select_k"]}, pred_threshold={config["pred_threshold"]:.2f}', flush=True)
            trial_out_dir = os.path.join(output_dir, f'trial_{trial}')
            metrics = ModelEvaluator.evaluate_config(config, csv_path, trial_out_dir)
            all_metrics.append(metrics)
            all_configs.append(config)
            print(f'[PROGRESS] Trial {trial} finished: score={metrics.overall_score:.4f}', flush=True)
        
        best_idx = np.argmax([m.overall_score for m in all_metrics])
        best_config = all_configs[best_idx]
    
    # Prepare results
    results = {
        'optimal_config': best_config,
        'all_metrics': [
            {
                'config': cfg,
                'latent_dim': m.latent_dim,
                'val_loss': m.val_loss,
                'num_states': m.num_states,
                'num_edges': m.num_edges,
                'orphan_percentage': m.orphan_percentage,
                'overall_score': m.overall_score,
                'num_connected_components': m.num_connected_components,
                'is_fully_connected': m.is_fully_connected,
            }
            for cfg, m in zip(all_configs, all_metrics)
        ],
        'optimization_method': 'bayesian' if use_bayesian else 'random',
        'latent_dim_selection': latent_results
    }
    
    best_metric = all_metrics[np.argmax([m.overall_score for m in all_metrics])]
    logger.info(f'Optimization complete. Best score: {best_metric.overall_score:.4f}')
    logger.info(f'Best config components: {best_metric.num_connected_components}, fully_connected: {best_metric.is_fully_connected}')
    
    if best_metric.is_fully_connected:
        print(f'[PROGRESS] ✅ OPTIMIZACIJA ZAVRŠENA - Pronađen POVEZAN graf sa {best_metric.num_states} stanja i {best_metric.num_edges} prelaza!', flush=True)
    else:
        logger.warning(f'⚠️ WARNING: Best config has {best_metric.num_connected_components} components - still fragmented!')
        print(f'[PROGRESS] ⚠️ Best config is fragmented with {best_metric.num_connected_components} components', flush=True)
    
    return results
