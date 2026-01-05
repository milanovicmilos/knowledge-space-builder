"""CLI command for building prerequisite graph and knowledge-space lattice.

Usage: python -m learning_space_generator.cli.build --pred PATH --item_cols PATH --out PATH --select_k 30 [--force_k]
"""
import argparse
import logging
from ..application.orchestrator import LearningSpaceBuilder, BuilderConfig
import numpy as np


def main(argv=None):
    parser = argparse.ArgumentParser(prog='lsg-build')
    parser.add_argument('--pred', required=True, help='Path to pred_probs.npy')
    parser.add_argument('--item_cols', required=True, help='Path to item_cols.npy')
    parser.add_argument('--out', default='learning_space_generator/output', help='Output directory')
    parser.add_argument('--select_k', type=int, default=30)
    parser.add_argument('--pred_threshold', type=float, default=0.6)
    parser.add_argument('--implication_threshold', type=float, default=0.85)
    parser.add_argument('--min_known', type=int, default=10)
    parser.add_argument('--min_support', type=int, default=0, help='Minimum support for empirical lattice (if >0 uses empirical approach)')
    parser.add_argument('--force_k', action='store_true')
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)
    # build config but do not retrain
    cfg = BuilderConfig(csv_path='', out_dir=args.out, pred_threshold=args.pred_threshold,
                        implication_threshold=args.implication_threshold, min_known=args.min_known,
                        select_k=args.select_k, force_k=args.force_k, min_support=args.min_support)
    builder = LearningSpaceBuilder(cfg)

    # Load preds and items
    preds = np.load(args.pred)
    items = np.load(args.item_cols, allow_pickle=True)

    # Phase2 only: prereq -> select -> lattice -> analyze
    G = builder.phase2_prereq(preds, args.item_cols)
    lattice_json, lattice_png = builder.phase2_select_and_build_lattice(G, args.pred, args.item_cols)
    summary_path, summary = builder.analyze(lattice_json, args.pred, args.item_cols)
    print('Done. Outputs:')
    print('lattice_json:', lattice_json)
    print('lattice_png:', lattice_png)
    print('summary_json:', summary_path)


if __name__ == '__main__':
    main()
