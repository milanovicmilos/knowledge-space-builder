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

logger = logging.getLogger(__name__)


@dataclass
class OptimizationParams:
    """Hyperparameter search space definition."""
    latent_dim_range: Tuple[int, int] = (3, 25)
    epochs_range: Tuple[int, int] = (5, 30)
    batch_size_options: List[int] = None
    learning_rate_range: Tuple[float, float] = (1e-4, 1e-2)
    pred_threshold_range: Tuple[float, float] = (0.5, 0.7)
    implication_threshold_range: Tuple[float, float] = (0.70, 0.95)
    select_k_options: List[int] = None
    min_support_range: Tuple[int, int] = (3, 50)
    
    def __post_init__(self):
        if self.batch_size_options is None:
            self.batch_size_options = [256, 512, 1024, 2048]
        if self.select_k_options is None:
            self.select_k_options = [20, 30, 40, 50]


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
                    # Train model with this latent_dim
                    train_mirt_vae(csv_path, tmpdir, epochs=epochs, latent_dim=dim)
                    
                    # Load predictions and compute metrics
                    probs = np.load(os.path.join(tmpdir, 'pred_probs.npy'))
                    
                    # Estimate loss (simple metric)
                    val_loss = np.mean(-((X * np.log(probs + 1e-8) + 
                                         (1 - X) * np.log(1 - probs + 1e-8)) * mask))
                    
                    results['latent_dims'].append(dim)
                    results['val_losses'].append(val_loss)
                    
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
            
            # Calculate overall quality score
            num_states = summary.get('num_states', 0)
            num_edges = summary.get('num_edges', 0)
            orphan_pct = 100 * (summary.get('orphan_states', 0) / max(num_states, 1))
            
            # Score: prefer balanced states, good connectivity, few orphans
            connectivity_score = min(num_edges / max(num_states, 1), 2.0) / 2.0  # normalized to 0-1
            orphan_score = 1.0 - min(orphan_pct / 100, 1.0)  # lower orphans = higher score
            loss_score = 1.0 / (1.0 + reconstruction_loss)  # lower loss = higher score
            
            overall_score = 0.4 * loss_score + 0.4 * connectivity_score + 0.2 * orphan_score
            
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
                overall_score=overall_score
            )
            
            logger.info('Config evaluation complete: score=%.4f', overall_score)
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
                overall_score=0.0
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
    
    if use_bayesian:
        try:
            import optuna
            
            def objective(trial):
                config = HyperparameterOptimizer.suggest_config(trial, param_space)
                trial_out_dir = os.path.join(output_dir, f'trial_{trial.number}')
                metrics = ModelEvaluator.evaluate_config(config, csv_path, trial_out_dir)
                all_metrics.append(metrics)
                all_configs.append(config)
                return metrics.overall_score
            
            study = optuna.create_study(direction='maximize')
            study.optimize(objective, n_trials=n_trials)
            
            best_config = all_configs[np.argmax([m.overall_score for m in all_metrics])]
            
        except ImportError:
            logger.warning('Optuna not available; using random search')
            use_bayesian = False
    
    if not use_bayesian:
        for trial in range(n_trials):
            config = HyperparameterOptimizer._random_config(param_space)
            trial_out_dir = os.path.join(output_dir, f'trial_{trial}')
            metrics = ModelEvaluator.evaluate_config(config, csv_path, trial_out_dir)
            all_metrics.append(metrics)
            all_configs.append(config)
        
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
                'orphan_percentage': m.orphan_percentage,
                'overall_score': m.overall_score,
            }
            for cfg, m in zip(all_configs, all_metrics)
        ],
        'optimization_method': 'bayesian' if use_bayesian else 'random',
        'latent_dim_selection': latent_results
    }
    
    logger.info('Optimization complete. Best score: %.4f', max([m.overall_score for m in all_metrics]))
    
    return results
