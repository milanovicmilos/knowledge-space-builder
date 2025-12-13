"""
NEAT (NeuroEvolution of Augmenting Topologies) algorithm for Learning Space Generation

This package contains the core NEAT implementation:
- structure.py: Knowledge state representation
- gene.py: Gene-level operations (mutation, crossover)
- genome.py: Learning space genome with NEAT operators
- runner.py: NEAT execution logic
"""

from .structure import KnowledgeState
from .gene import Gene, KnowledgeStateGene
from .genome import LearningSpaceGenome, LearningSpaceGenomeConfig
from .runner import run_neat

__all__ = [
    'KnowledgeState',
    'Gene',
    'KnowledgeStateGene',
    'LearningSpaceGenome',
    'LearningSpaceGenomeConfig',
    'run_neat'
]
