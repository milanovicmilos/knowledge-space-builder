"""
Learning Space Generation Algorithms

This package contains different algorithms for generating and analyzing learning spaces:
- NEAT: NeuroEvolution of Augmenting Topologies (genetic algorithm)
- IITA: Inductive Item Tree Analysis (prerequisite structure discovery)
"""

from . import neat, iita

__all__ = ['neat', 'iita']
