"""Core orchestrator for the learning_space_generator pipeline.

This module provides a single class `LearningSpaceBuilder` that implements
the two-phase pipeline (probabilistic modeling -> knowledge-space construction)
while keeping a clean, testable interface.
"""
from dataclasses import dataclass
import os
import logging
from typing import Optional
import numpy as np

from ..infrastructure import data_loader, model_trainer
from ..infrastructure.visualization import save_graph_png
from ..domain.services import prerequisite_builder, lattice_builder, analyzer

logger = logging.getLogger(__name__)


@dataclass
class BuilderConfig:
    csv_path: str
    out_dir: str = 'learning_space_generator/output'
    epochs: int = 8
    latent: int = 10
    pred_threshold: float = 0.6
    implication_threshold: float = 0.85
    min_known: int = 10
    select_k: int = 30
    force_k: bool = False
    min_support: int = 5


class LearningSpaceBuilder:
    def __init__(self, cfg: BuilderConfig):
        self.cfg = cfg
        os.makedirs(self.cfg.out_dir, exist_ok=True)

    def phase1_train(self, run_train: bool = True):
        """Phase 1: train or load probabilistic model and produce pred_probs + item_cols."""
        pred_path = os.path.join(self.cfg.out_dir, 'pred_probs.npy')
        items_path = os.path.join(self.cfg.out_dir, 'item_cols.npy')
        if run_train:
            logger.info('Phase1: Training MIRT-VAE (epochs=%d, latent=%d)', self.cfg.epochs, self.cfg.latent)
            probs = model_trainer.main(self.cfg.csv_path, self.cfg.out_dir, epochs=self.cfg.epochs, latent_dim=self.cfg.latent)
            # model_trainer.main saves pred_probs.npy and item_cols.npy
            return probs, items_path
        else:
            # load existing
            logger.info('Phase1: Loading existing pred_probs from %s', pred_path)
            probs = np.load(pred_path)
            return probs, items_path

    def phase2_prereq(self, pred_probs: np.ndarray, item_cols_path: str):
        """Infer prerequisite graph from predictions."""
        items = np.load(item_cols_path, allow_pickle=True)
        G = prerequisite_builder.build_prereq_graph(pred_probs, items, pred_threshold=self.cfg.pred_threshold,
                                      implication_threshold=self.cfg.implication_threshold,
                                      min_known=self.cfg.min_known)
        prereq_json = os.path.join(self.cfg.out_dir, 'prereq_graph.json')
        prerequisite_builder.save_graph_json(G, prereq_json)
        try:
            prereq_png = os.path.join(self.cfg.out_dir, 'prereq_graph.png')
            save_graph_png(G, prereq_png)
        except Exception:
            logger.debug('Could not save prereq PNG')
        return G

    def phase2_select_and_build_lattice(self, G, pred_probs_path: str, item_cols_path: str):
        """Select top-k and build lattice. Uses empirical approach when min_support > 0."""
        import numpy as np
        from collections import Counter
        
        if self.cfg.min_support > 0:
            # Empirical approach: binarize -> frequent states -> poset (like old ms30 run)
            logger.info('Using empirical lattice approach (min_support=%d)', self.cfg.min_support)
            probs = np.load(pred_probs_path)
            items = np.load(item_cols_path, allow_pickle=True)
            selected = lattice_builder.select_by_degree(G, self.cfg.select_k)
            # filter to selected items
            item_list = [str(x) for x in items]
            selected_indices = [item_list.index(it) for it in selected if it in item_list]
            probs_subset = probs[:, selected_indices]
            binary = probs_subset >= self.cfg.pred_threshold
            # build observed states
            states_list = []
            selected_names = [item_list[i] for i in selected_indices]
            for row in binary:
                s = frozenset([selected_names[j] for j, v in enumerate(row) if v])
                states_list.append(s)
            cnt = Counter(states_list)
            frequent = [s for s, c in cnt.items() if c >= self.cfg.min_support]
            if frozenset() not in frequent:
                frequent.insert(0, frozenset())
            logger.info('Empirical: %d frequent states from %d unique (threshold=%d)', len(frequent), len(cnt), self.cfg.min_support)
            states = set(frequent)
        else:
            # Full enumeration approach
            selected = lattice_builder.select_by_degree(G, self.cfg.select_k)
            if self.cfg.force_k:
                # estimate before attempting full enumeration to avoid MemoryError
                est = lattice_builder.count_ideals_from_dag(G, items=selected, cap=10000000)
                logger.info('Forcing k=%d selection (estimated ideals=%s)', self.cfg.select_k, est)
                if est is not None and est > 2000000:
                    raise RuntimeError(f'Forcing k={self.cfg.select_k} would generate ~{est} ideals which exceeds safety limits; unset force_k or choose smaller k')
                states = lattice_builder.generate_learning_space_from_dag(G, items=selected)
            else:
                est = lattice_builder.count_ideals_from_dag(G, items=selected, cap=1000000)
                logger.info('Selected top-%d items (est ideals=%s)', self.cfg.select_k, est)
                if est is not None and est > 1000000:
                    # reduce until manageable
                    k = self.cfg.select_k
                    while est and est > 1000000 and k > 2:
                        k = max(2, k // 2)
                        selected = lattice_builder.select_by_degree(G, k)
                        est = lattice_builder.count_ideals_from_dag(G, items=selected, cap=1000000)
                        logger.warning('Reduced k to %d estimate=%s', k, est)
                states = lattice_builder.generate_learning_space_from_dag(G, items=selected)

        closed_list = sorted(list(states), key=lambda s: (len(s), tuple(sorted(s))))
        poset = lattice_builder.build_poset_from_sets(closed_list)
        out_json = os.path.join(self.cfg.out_dir, f'knowledge_space_lattice_k{self.cfg.select_k}.json')
        with open(out_json, 'w', encoding='utf-8') as f:
            import json
            json.dump(poset, f, indent=2, ensure_ascii=False)
        out_png = os.path.join(self.cfg.out_dir, f'knowledge_space_lattice_k{self.cfg.select_k}.png')
        lattice_builder.save_hasse(poset, out_png)
        return out_json, out_png

    def analyze(self, lattice_json: str, pred_probs_path: str, item_cols_path: str):
        summary = analyzer.analyze_lattice(lattice_json, pred_probs=pred_probs_path, item_cols=item_cols_path,
                                          pred_threshold=self.cfg.pred_threshold)
        out_sum = os.path.join(self.cfg.out_dir, f'knowledge_space_k{self.cfg.select_k}_summary.json')
        import json
        with open(out_sum, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        return out_sum, summary

    def run_all(self, run_train: bool = True):
        probs, items_path = self.phase1_train(run_train=run_train)
        pred_path = os.path.join(self.cfg.out_dir, 'pred_probs.npy')
        G = self.phase2_prereq(probs, items_path)
        lattice_json, lattice_png = self.phase2_select_and_build_lattice(G, pred_path, items_path)
        summary_path, summary = self.analyze(lattice_json, pred_path, items_path)
        return dict(pred_probs=pred_path, item_cols=items_path, prereq=os.path.join(self.cfg.out_dir,'prereq_graph.json'), lattice_json=lattice_json, lattice_png=lattice_png, summary_json=summary_path)
