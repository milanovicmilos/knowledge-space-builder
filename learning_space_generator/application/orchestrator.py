"""Core orchestrator for the learning_space_generator pipeline.

This module provides a single class `LearningSpaceBuilder` that implements
the two-phase pipeline (probabilistic modeling -> knowledge-space construction)
while keeping a clean, testable interface.
"""
from dataclasses import dataclass
import os
import logging
from typing import Optional, Dict, Any
import numpy as np
import json
from collections import Counter

from ..infrastructure.model_trainer import main as train_mirt_vae
from ..infrastructure.data_loader import load_response_csv, save_output_arrays
from ..domain.services.prerequisite_builder import build_prereq_graph, save_graph_json
from ..domain.services.lattice_builder import (
    select_by_degree, 
    generate_learning_space_from_dag,
    build_poset_from_sets,
    count_ideals_from_dag
)
from ..domain.services.analyzer import analyze_lattice
from ..infrastructure.visualization import save_hasse_diagram

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
    min_support: int = 7


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
            train_mirt_vae(self.cfg.csv_path, self.cfg.out_dir, epochs=self.cfg.epochs, latent_dim=self.cfg.latent)
            # train_mirt_vae saves pred_probs.npy and item_cols.npy
            probs = np.load(pred_path)
            return probs, items_path
        else:
            # load existing
            logger.info('Phase1: Loading existing pred_probs from %s', pred_path)
            probs = np.load(pred_path)
            return probs, items_path

    def phase2_prereq(self, pred_probs: np.ndarray, item_cols_path: str):
        """Infer prerequisite graph from predictions."""
        items = np.load(item_cols_path, allow_pickle=True)
        G = build_prereq_graph(pred_probs, items, pred_threshold=self.cfg.pred_threshold,
                                      implication_threshold=self.cfg.implication_threshold,
                                      min_known=self.cfg.min_known)
        prereq_json = os.path.join(self.cfg.out_dir, 'prereq_graph.json')
        save_graph_json(G, prereq_json)
        try:
            prereq_png = os.path.join(self.cfg.out_dir, 'prereq_graph.png')
            save_hasse_diagram(G, prereq_png)
        except Exception as e:
            logger.debug(f'Could not save prereq PNG: {e}')
        return G

    def phase2_select_and_build_lattice(self, G, pred_probs_path: str, item_cols_path: str):
        """Select top-k and build lattice. Uses empirical approach when min_support > 0."""
        
        if self.cfg.min_support > 0:
            # Empirical approach: binarize -> frequent states -> poset
            logger.info('Using empirical lattice approach (min_support=%d)', self.cfg.min_support)
            probs = np.load(pred_probs_path)
            items = np.load(item_cols_path, allow_pickle=True)
            selected = select_by_degree(G, self.cfg.select_k)
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
            selected = select_by_degree(G, self.cfg.select_k)
            if self.cfg.force_k:
                # estimate before attempting full enumeration to avoid MemoryError
                est = count_ideals_from_dag(G, items=selected, cap=10000000)
                logger.info('Forcing k=%d selection (estimated ideals=%s)', self.cfg.select_k, est)
                if est is not None and est > 2000000:
                    raise RuntimeError(f'Forcing k={self.cfg.select_k} would generate ~{est} ideals which exceeds safety limits; unset force_k or choose smaller k')
                states = generate_learning_space_from_dag(G, items=selected)
            else:
                est = count_ideals_from_dag(G, items=selected, cap=1000000)
                logger.info('Selected top-%d items (est ideals=%s)', self.cfg.select_k, est)
                if est is not None and est > 1000000:
                    # reduce until manageable
                    k = self.cfg.select_k
                    while est and est > 1000000 and k > 2:
                        k = max(2, k // 2)
                        selected = select_by_degree(G, k)
                        est = count_ideals_from_dag(G, items=selected, cap=1000000)
                        logger.warning('Reduced k to %d estimate=%s', k, est)
                states = generate_learning_space_from_dag(G, items=selected)

        closed_list = sorted(list(states), key=lambda s: (len(s), tuple(sorted(s))))
        poset = build_poset_from_sets(closed_list)
        out_json = os.path.join(self.cfg.out_dir, f'knowledge_space_lattice_k{self.cfg.select_k}.json')
        with open(out_json, 'w', encoding='utf-8') as f:
            json.dump(poset, f, indent=2, ensure_ascii=False)
        out_png = os.path.join(self.cfg.out_dir, f'knowledge_space_lattice_k{self.cfg.select_k}.png')
        try:
            save_hasse_diagram(poset, out_png)
        except Exception as e:
            logger.debug(f'Could not save lattice PNG: {e}')
        return out_json, out_png

    def analyze(self, lattice_json: str, pred_probs_path: str, item_cols_path: str) -> Dict[str, Any]:
        summary = analyze_lattice(lattice_json, pred_probs=pred_probs_path, item_cols=item_cols_path,
                                          pred_threshold=self.cfg.pred_threshold)
        out_sum = os.path.join(self.cfg.out_dir, f'knowledge_space_k{self.cfg.select_k}_summary.json')
        with open(out_sum, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        return out_sum, summary

    def run_all(self, run_train: bool = True) -> Dict[str, str]:
        probs, items_path = self.phase1_train(run_train=run_train)
        pred_path = os.path.join(self.cfg.out_dir, 'pred_probs.npy')
        G = self.phase2_prereq(probs, items_path)
        lattice_json, lattice_png = self.phase2_select_and_build_lattice(G, pred_path, items_path)
        summary_path, summary = self.analyze(lattice_json, pred_path, items_path)
        return dict(
            pred_probs=pred_path, 
            item_cols=items_path, 
            prereq=os.path.join(self.cfg.out_dir,'prereq_graph.json'), 
            lattice_json=lattice_json, 
            lattice_png=lattice_png, 
            summary_json=summary_path
        )
