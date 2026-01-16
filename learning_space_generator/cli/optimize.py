"""CLI for running comprehensive model optimization and evaluation."""

import argparse
import logging
import sys
import json
import os
from pathlib import Path

# Force line buffering for stdout to ensure prints reach subprocess parent immediately
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main_optimize(args):
    """Run hyperparameter optimization."""
    from ..infrastructure.model_selection import find_optimal_hyperparameters, OptimizationParams
    
    logger.info('Starting hyperparameter optimization')
    logger.info('CSV: %s', args.csv)
    logger.info('Number of trials: %d', args.n_trials)
    
    # Create parameter space if custom not provided
    param_space = OptimizationParams()
    if args.latent_dim_range:
        param_space.latent_dim_range = tuple(args.latent_dim_range)
    
    # Run optimization
    results = find_optimal_hyperparameters(
        csv_path=args.csv,
        output_dir=args.out_dir,
        n_trials=args.n_trials,
        use_bayesian=not args.no_bayesian,
        param_space=param_space
    )
    
    # Save results
    results_path = os.path.join(args.out_dir, 'optimization_results.json')
    with open(results_path, 'w') as f:
        # Convert metrics to dict for JSON serialization
        results['all_metrics'] = [
            {k: (v if isinstance(v, (int, float, str)) else str(v)) 
             for k, v in m.items()}
            for m in results['all_metrics']
        ]
        json.dump(results, f, indent=2, default=str)
    
    logger.info('Optimization results saved to %s', results_path)
    logger.info('Optimal config: %s', results['optimal_config'])
    
    return results


def main_evaluate(args):
    """Run evaluation on dataset."""
    from ..infrastructure.quality_metrics import QualityReport
    
    logger.info('Running quality evaluation')
    logger.info('Lattice: %s', args.lattice)
    
    # Generate quality report
    report = QualityReport.generate_report(
        csv_path=args.csv,
        lattice_json_path=args.lattice,
        pred_probs_path=args.pred_probs,
        item_cols_path=args.item_cols,
        prereq_graph_path=args.prereq,
        pred_threshold=args.pred_threshold,
        implication_threshold=args.implication_threshold,
        output_path=args.output
    )
    
    # Print summary
    logger.info('=== Quality Report Summary ===')
    logger.info('Dataset: %d students, %d items', 
                report['dataset_info']['num_students'],
                report['dataset_info']['num_items'])
    
    ks_metrics = report['knowledge_space_metrics']
    logger.info('Knowledge Space: %d states, %d edges',
                ks_metrics['connectivity']['num_states'],
                ks_metrics['connectivity']['num_edges'])
    logger.info('Orphan States: %.1f%%', ks_metrics['orphans']['orphan_percentage'])
    logger.info('State Coverage: %.1f%%', ks_metrics['coverage']['coverage_percentage'])
    
    logger.info('=== Recommendations ===')
    for rec in report['recommendations']:
        logger.info(rec)
    
    return report


def main_manual_pipeline(args):
    """Run full pipeline with manually specified parameters."""
    from ..infrastructure.model_selection import OptimizationParams
    from ..application.orchestrator import LearningSpaceBuilder, BuilderConfig
    from ..infrastructure.quality_metrics import QualityReport
    
    logger.info('Starting manual pipeline: train → build → evaluate')
    
    # 1. Build config from args
    logger.info('=== Phase 1: Configuring Pipeline ===')
    
    builder_config = BuilderConfig(
        csv_path=args.csv,
        out_dir=args.out_dir,
        epochs=args.epochs,
        latent=args.latent_dim,
        pred_threshold=args.pred_threshold,
        implication_threshold=args.implication_threshold,
        select_k=args.select_k,
        min_support=args.min_support,
        min_known=args.min_known
    )
    
    # Save manual config for reference
    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, 'manual_config.json'), 'w') as f:
        json.dump(vars(builder_config), f, indent=2, default=str)

    # 2. Run Pipeline
    logger.info('=== Phase 2: Execution (Train & Build) ===')
    builder = LearningSpaceBuilder(builder_config)
    results = builder.run_all(run_train=True)
    
    # 3. Evaluate quality
    logger.info('=== Phase 3: Quality Evaluation ===')
    
    lattice_json = results['lattice_json']
    pred_probs = results['pred_probs']
    item_cols = results['item_cols']
    prereq = results['prereq']
    
    report = QualityReport.generate_report(
        csv_path=args.csv,
        lattice_json_path=lattice_json,
        pred_probs_path=pred_probs,
        item_cols_path=item_cols,
        prereq_graph_path=prereq,
        pred_threshold=args.pred_threshold,
        implication_threshold=args.implication_threshold,
        output_path=os.path.join(args.out_dir, 'quality_report.json')
    )
    
    # Log summary
    logger.info('=== Final Quality Report ===')
    logger.info(f"Dataset: {report['dataset_info']['num_students']} students, {report['dataset_info']['num_items']} items")
    logger.info(f"Knowledge Space: {report['knowledge_space_metrics']['connectivity']['num_states']} states, "
                f"{report['knowledge_space_metrics']['connectivity']['num_edges']} edges")


def main_full_pipeline(args):
    """Run full pipeline: optimization + build + evaluate."""
    from ..infrastructure.model_selection import find_optimal_hyperparameters, OptimizationParams
    from ..application.orchestrator import LearningSpaceBuilder, BuilderConfig
    from ..infrastructure.quality_metrics import QualityReport
    
    logger.info('Starting full pipeline: optimize → build → evaluate')
    
    # 1. Optimize hyperparameters
    logger.info('=== Phase 1: Hyperparameter Optimization ===')
    
    param_space = OptimizationParams()
    opt_results = find_optimal_hyperparameters(
        csv_path=args.csv,
        output_dir=args.out_dir,
        n_trials=args.n_trials,
        use_bayesian=True,
        param_space=param_space
    )
    
    optimal_config = opt_results['optimal_config']
    
    # 2. Build final knowledge space with optimal config
    logger.info('=== Phase 2: Building Knowledge Space with Optimal Config ===')
    
    builder_config = BuilderConfig(
        csv_path=args.csv,
        out_dir=args.out_dir,
        epochs=optimal_config['epochs'],
        latent=optimal_config['latent_dim'],
        pred_threshold=optimal_config['pred_threshold'],
        implication_threshold=optimal_config['implication_threshold'],
        select_k=optimal_config['select_k'],
        min_support=optimal_config['min_support']
    )
    
    builder = LearningSpaceBuilder(builder_config)
    results = builder.run_all(run_train=True)
    
    # 3. Evaluate quality
    logger.info('=== Phase 3: Quality Evaluation ===')
    
    lattice_json = results['lattice_json']
    pred_probs = results['pred_probs']
    item_cols = results['item_cols']
    prereq = results['prereq']
    
    report = QualityReport.generate_report(
        csv_path=args.csv,
        lattice_json_path=lattice_json,
        pred_probs_path=pred_probs,
        item_cols_path=item_cols,
        prereq_graph_path=prereq,
        pred_threshold=optimal_config['pred_threshold'],
        implication_threshold=optimal_config['implication_threshold'],
        output_path=os.path.join(args.out_dir, 'quality_report.json')
    )
    
    # Print full report
    logger.info('=== Final Quality Report ===')
    logger.info('Dataset: %d students, %d items',
                report['dataset_info']['num_students'],
                report['dataset_info']['num_items'])
    
    ks = report['knowledge_space_metrics']
    logger.info('Knowledge Space: %d states, %d edges, %.1f%% orphans',
                ks['connectivity']['num_states'],
                ks['connectivity']['num_edges'],
                ks['orphans']['orphan_percentage'])
    
    logger.info('Reconstruction Accuracy: %.2f%%', 
                report['vae_metrics']['reconstruction']['prediction_accuracy'] * 100)
    
    logger.info('=== Recommendations ===')
    for rec in report['recommendations']:
        logger.info(rec)
    
    # Save final config
    final_config_path = os.path.join(args.out_dir, 'optimal_config.json')
    
    # Helper to convert numpy types
    def default_converter(o):
        import numpy as np
        if isinstance(o, (np.int_, np.intc, np.intp, np.int8,
                          np.int16, np.int32, np.int64, np.uint8,
                          np.uint16, np.uint32, np.uint64)):
            return int(o)
        elif isinstance(o, (np.float_, np.float16, np.float32, np.float64)):
            return float(o)
        elif isinstance(o, (np.ndarray,)):
            return o.tolist()
        raise TypeError(f'Object of type {o.__class__.__name__} is not JSON serializable')

    with open(final_config_path, 'w') as f:
        json.dump(optimal_config, f, indent=2, default=default_converter)
    logger.info('Optimal config saved to %s', final_config_path)
    
    return {'optimization': opt_results, 'quality_report': report, 'results': results}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='MIRT-VAE Optimization and Evaluation Suite')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Optimize command
    opt_parser = subparsers.add_parser('optimize', help='Run hyperparameter optimization')
    opt_parser.add_argument('--csv', required=True, help='Input CSV file')
    opt_parser.add_argument('--out_dir', default='learning_space_generator/output', help='Output directory')
    opt_parser.add_argument('--n_trials', type=int, default=10, help='Number of trials')
    opt_parser.add_argument('--latent_dim_range', type=int, nargs=2, default=None, help='Latent dim range')
    opt_parser.add_argument('--no_bayesian', action='store_true', help='Use random search instead of Bayesian')
    opt_parser.set_defaults(func=main_optimize)
    
    # Evaluate command
    eval_parser = subparsers.add_parser('evaluate', help='Run quality evaluation')
    eval_parser.add_argument('--csv', required=True, help='Input CSV file')
    eval_parser.add_argument('--lattice', required=True, help='Lattice JSON file')
    eval_parser.add_argument('--pred_probs', required=True, help='Predictions NPY file')
    eval_parser.add_argument('--item_cols', required=True, help='Item columns NPY file')
    eval_parser.add_argument('--prereq', required=True, help='Prerequisite graph JSON file')
    eval_parser.add_argument('--pred_threshold', type=float, default=0.6, help='Prediction threshold')
    eval_parser.add_argument('--implication_threshold', type=float, default=0.85, help='Implication threshold')
    eval_parser.add_argument('--output', default=None, help='Output report path')
    eval_parser.set_defaults(func=main_evaluate)
    
    # Full pipeline command
    full_parser = subparsers.add_parser('full', help='Run full optimization + build + evaluate pipeline')
    full_parser.add_argument('--csv', required=True, help='Input CSV file')
    full_parser.add_argument('--out_dir', default='learning_space_generator/output', help='Output directory')
    full_parser.add_argument('--n_trials', type=int, default=10, help='Number of optimization trials')
    full_parser.set_defaults(func=main_full_pipeline)

    # Manual pipeline command
    manual_parser = subparsers.add_parser('manual', help='Run manual build + evaluate pipeline')
    manual_parser.add_argument('--csv', required=True, help='Input CSV file')
    manual_parser.add_argument('--out_dir', default='learning_space_generator/output', help='Output directory')
    manual_parser.add_argument('--epochs', type=int, default=100, help='Number of training epochs')
    manual_parser.add_argument('--latent_dim', type=int, default=5, help='Latent dimension size')
    manual_parser.add_argument('--select_k', type=int, default=5, help='Number of implications per item')
    manual_parser.add_argument('--pred_threshold', type=float, default=0.6, help='Prediction threshold')
    manual_parser.add_argument('--implication_threshold', type=float, default=0.85, help='Implication threshold')
    manual_parser.add_argument('--min_support', type=int, default=5, help='Minimum support for implications')
    manual_parser.add_argument('--min_known', type=int, default=2, help='Minimum known items per user')
    manual_parser.set_defaults(func=main_manual_pipeline)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Run command
    result = args.func(args)
    logger.info('Command %s completed successfully', args.command)
