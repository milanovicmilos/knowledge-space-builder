"""
IITA (Inductive Item Tree Analysis) Algorithm

This package contains IITA implementation for discovering prerequisite structures:
- analyzer.py: Core IITAAnalyzer class with diff computation and graph building
- runner.py: Execution logic for running IITA analysis
"""

from .analyzer import IITAAnalyzer
from .runner import run_iita_analysis

__all__ = [
    'IITAAnalyzer',
    'run_iita_analysis'
]
