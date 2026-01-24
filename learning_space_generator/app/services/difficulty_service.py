"""
Difficulty Analysis Service
============================

This service calculates item difficulty and sorts items within each concept
by their difficulty level (from easiest to hardest).

Difficulty is measured as the percentage of students who answered correctly.
"""

import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
from learning_space_generator.app.core.config import settings
import logging

logger = logging.getLogger(__name__)



class DifficultyService:
    """Service for analyzing item difficulty and sorting items within concepts."""
    
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or settings.OUTPUT_DIR
        
    def calculate_item_difficulties(self, data_path: Path = None) -> Dict[str, float]:
        """
        Calculate difficulty for each item based on student responses.
        
        Difficulty = % of correct responses (higher % = easier item)
        
        Args:
            data_path: Path to cleaned responses CSV
            
        Returns:
            Dictionary mapping item_id -> difficulty_score (0.0 to 1.0)
        """
        if data_path is None:
            data_path = self.output_dir / "cleaned_responses.csv"
            
        logger.info(f"📊 Calculating item difficulties from: {data_path}")
        
        # Load student responses
        df = pd.read_csv(data_path)
        
        # Calculate mean for each column (item)
        # Higher mean = easier item (more students got it right)
        difficulties = {}
        
        for column in df.columns:
            if column.startswith('s'):  # Item columns start with 's'
                mean_score = df[column].mean()
                difficulties[column] = float(mean_score)
                
        logger.info(f"✅ Calculated difficulties for {len(difficulties)} items")
        logger.info(f"   Difficulty range: {min(difficulties.values()):.2%} - {max(difficulties.values()):.2%}")
        
        return difficulties
    
    def sort_items_by_difficulty(
        self,
        concept_mapping_path: Path = None,
        difficulties: Dict[str, float] = None
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        Sort items within each concept by difficulty (easiest -> hardest).
        
        Args:
            concept_mapping_path: Path to concept_to_items_mapping.json
            difficulties: Pre-calculated difficulties (if None, will calculate)
            
        Returns:
            Dictionary mapping concept_name -> [(item_id, difficulty), ...]
            Items are sorted from EASIEST (highest %) to HARDEST (lowest %)
        """
        if concept_mapping_path is None:
            concept_mapping_path = self.output_dir / "concept_to_items_mapping.json"
            
        if difficulties is None:
            difficulties = self.calculate_item_difficulties()
            
        logger.info(f"📚 Sorting items by difficulty within concepts...")
        
        # Load concept mapping
        with open(concept_mapping_path, 'r', encoding='utf-8') as f:
            concept_mapping = json.load(f)
            
        # Sort items within each concept
        sorted_concepts = {}
        
        for concept_name, items in concept_mapping.items():
            # Get difficulty for each item
            items_with_difficulty = []
            for item_id in items:
                if item_id in difficulties:
                    items_with_difficulty.append((item_id, difficulties[item_id]))
                else:
                    logger.warning(f"⚠️  Item {item_id} not found in difficulties")
                    
            # Sort by difficulty (descending = easiest first)
            items_with_difficulty.sort(key=lambda x: x[1], reverse=True)
            
            sorted_concepts[concept_name] = items_with_difficulty
            
            if items_with_difficulty:
                easiest_diff = items_with_difficulty[0][1]
                hardest_diff = items_with_difficulty[-1][1]
                logger.info(f"   {concept_name}: {len(items_with_difficulty)} items, "
                          f"difficulty range {hardest_diff:.1%} - {easiest_diff:.1%}")
            
        return sorted_concepts
    
    def run_difficulty_analysis(self) -> Path:
        """
        Complete difficulty analysis pipeline.
        
        Returns:
            Path to the output JSON file
        """
        logger.info("=" * 80)
        logger.info("DIFFICULTY ANALYSIS - Sorting Items by Difficulty")
        logger.info("=" * 80)
        
        # Calculate difficulties
        difficulties = self.calculate_item_difficulties()
        
        # Sort items within concepts
        sorted_concepts = self.sort_items_by_difficulty(difficulties=difficulties)
        
        # Save item difficulties
        difficulties_path = self.output_dir / "item_difficulties.json"
        with open(difficulties_path, 'w', encoding='utf-8') as f:
            json.dump(difficulties, f, indent=2, ensure_ascii=False)
        logger.info(f"💾 Saved item difficulties to: {difficulties_path}")
        
        # Save sorted concepts
        sorted_path = self.output_dir / "concepts_sorted_by_difficulty.json"
        
        # Convert to serializable format
        serializable_data = {
            concept: [
                {
                    "item_id": item_id,
                    "difficulty": round(diff, 4),
                    "difficulty_percent": f"{diff:.1%}",
                    "rank": idx + 1
                }
                for idx, (item_id, diff) in enumerate(items)
            ]
            for concept, items in sorted_concepts.items()
        }
        
        with open(sorted_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_data, f, indent=2, ensure_ascii=False)
            
        logger.info(f"💾 Saved sorted concepts to: {sorted_path}")
        logger.info("=" * 80)
        logger.info(f"✅ Difficulty analysis complete!")
        logger.info(f"   - {len(difficulties)} items analyzed")
        logger.info(f"   - {len(sorted_concepts)} concepts sorted")
        logger.info("=" * 80)
        
        return sorted_path


def main():
    """CLI entry point for difficulty analysis."""
    service = DifficultyService()
    service.run_difficulty_analysis()


if __name__ == "__main__":
    main()
