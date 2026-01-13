#!/usr/bin/env python
"""Quick test of optimization pipeline."""

import logging
import sys
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    from learning_space_generator.infrastructure.quality_metrics import QualityReport
    
    logger.info('Testing quality metrics on existing results')
    
    # Use results from previous run
    csv_path = 'learning_space_generator/data/ResponsePatterns_Stellwerk_Math_2018-2024(in).csv'
    lattice_path = 'learning_space_generator/output/knowledge_space_lattice_k30.json'
    pred_probs_path = 'learning_space_generator/output/pred_probs.npy'
    item_cols_path = 'learning_space_generator/output/item_cols.npy'
    prereq_path = 'learning_space_generator/output/prereq_graph.json'
    
    # Check if files exist
    files_ok = all(os.path.exists(p) for p in [lattice_path, pred_probs_path, item_cols_path, prereq_path])
    
    if not files_ok:
        logger.error('Output files not found. Run pipeline first.')
        sys.exit(1)
    
    logger.info('Generating quality report...')
    report = QualityReport.generate_report(
        csv_path=csv_path,
        lattice_json_path=lattice_path,
        pred_probs_path=pred_probs_path,
        item_cols_path=item_cols_path,
        prereq_graph_path=prereq_path,
        output_path='learning_space_generator/output/quality_report.json'
    )
    
    logger.info('=== QUALITY REPORT SUMMARY ===')
    logger.info('Dataset: %d students x %d items',
                report['dataset_info']['num_students'],
                report['dataset_info']['num_items'])
    
    vae = report['vae_metrics']['reconstruction']
    logger.info('VAE Prediction Accuracy: %.2f%%',  vae.get('prediction_accuracy', 0) * 100)
    logger.info('  - Items <80%% accuracy: %d', vae.get('items_below_80_accuracy', 0))
    
    ks = report['knowledge_space_metrics']
    conn = ks['connectivity']
    logger.info('Knowledge Space:')
    logger.info('  - States: %d', conn['num_states'])
    logger.info('  - Edges: %d', conn['num_edges'])
    logger.info('  - Components: %d', conn['connected_components'])
    
    logger.info('Lattice Quality:')
    orphans = ks['orphans']
    logger.info('  - Orphan states: %.1f%%', orphans['orphan_percentage'])
    cov = ks['coverage']
    logger.info('  - Coverage: %.1f%%', cov.get('coverage_percentage', 0))
    logger.info('  - Avg degree: %.2f', conn['average_degree'])
    
    logger.info('Prerequisites:')
    prereq = ks['prerequisites']
    logger.info('  - Count: %d', prereq.get('prerequisite_count', 0))
    logger.info('  - Mean implication rate: %.3f', prereq.get('mean_implication_rate', 0))
    
    logger.info('=== RECOMMENDATIONS ===')
    for rec in report['recommendations']:
        logger.info(rec)
    
    logger.info('Quality report saved!')
