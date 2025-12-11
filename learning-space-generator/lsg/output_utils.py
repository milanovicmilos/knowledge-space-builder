"""Utilities for handling output files and directories."""

import os
from pathlib import Path


# Output directory structure
OUTPUT_DIR = Path(__file__).parent.parent / "output"
VISUALIZATIONS_DIR = OUTPUT_DIR / "visualizations"
DATA_DIR = OUTPUT_DIR / "data"
MODELS_DIR = OUTPUT_DIR / "models"


def ensure_output_dirs() -> None:
    """Create output directory structure if it doesn't exist."""
    for directory in [OUTPUT_DIR, VISUALIZATIONS_DIR, DATA_DIR, MODELS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def get_visualization_path(filename: str) -> str:
    """Get full path for visualization file in output/visualizations/."""
    ensure_output_dirs()
    return str(VISUALIZATIONS_DIR / filename)


def get_data_path(filename: str) -> str:
    """Get full path for data file in output/data/."""
    ensure_output_dirs()
    return str(DATA_DIR / filename)


def get_model_path(filename: str) -> str:
    """Get full path for model file in output/models/."""
    ensure_output_dirs()
    return str(MODELS_DIR / filename)


def get_default_output_paths(base_name: str = "learning_space") -> dict:
    """Get default output paths for all output files."""
    ensure_output_dirs()
    return {
        "visualization": str(VISUALIZATIONS_DIR / f"{base_name}.png"),
        "json": str(DATA_DIR / f"{base_name}.json"),
        "model": str(MODELS_DIR / f"{base_name}.pkl"),
    }
