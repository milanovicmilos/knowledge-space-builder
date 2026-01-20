"""
Concept Aggregation Service
============================
Agregira studentske odgovore sa nivoa pojedinačnih pitanja na nivo mastery po konceptu.

Pipeline:
1. Load LLM item classifications (pitanje → koncept)
2. Load student responses (students × items)
3. Agregacija: Za svakog studenta i koncept → mastery score
4. Output: Agregirana matrica (students × concepts)

Ovo omogućava da IITA radi na stabilnijim, semantički smislenim varijablama.
"""

import pandas as pd
import numpy as np
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

from learning_space_generator.app.core.config import settings

logger = logging.getLogger(__name__)


class ConceptAggregationService:
    """Agregira item-level responses u concept-level mastery scores"""
    
    def __init__(self):
        self.item_to_concept: Dict[str, str] = {}
        self.concept_to_items: Dict[str, List[str]] = defaultdict(list)
        self.unique_concepts: List[str] = []
        
    def load_item_classifications(self, classifications_file: Path) -> None:
        """
        Load LLM item classifications (već generisano u semantic_service)
        
        Args:
            classifications_file: Path to llm_item_classifications.json
        """
        logger.info(f"Loading item classifications from {classifications_file}")
        
        with open(classifications_file, 'r', encoding='utf-8') as f:
            self.item_to_concept = json.load(f)
        
        # Inverzno mapiranje: koncept → items
        for item, concept in self.item_to_concept.items():
            # Skip "Unbekannt" / "Unclassified" items
            if concept not in ["Unbekannt", "Unclassified", "Unknown"]:
                self.concept_to_items[concept].append(item)
        
        self.unique_concepts = sorted(self.concept_to_items.keys())
        
        logger.info(f"Loaded {len(self.item_to_concept)} items mapped to {len(self.unique_concepts)} concepts")
        logger.info(f"Concepts: {', '.join(self.unique_concepts[:10])}...")
        
    def aggregate_to_concepts(
        self, 
        data_file: Path,
        output_file: Path
    ) -> Tuple[pd.DataFrame, Dict[str, List[str]]]:
        """
        Agregira student responses na concept-level mastery scores
        
        Args:
            data_file: Path to cleaned CSV (students × items)
            output_file: Path to save aggregated CSV (students × concepts)
            
        Returns:
            Tuple of (aggregated_df, concept_to_items mapping)
        """
        logger.info(f"Aggregating data from {data_file}")
        
        # Load student data
        df = pd.read_csv(data_file)
        logger.info(f"Loaded data: {df.shape[0]} students, {df.shape[1]} columns")
        
        # Identify item columns (exclude student_id if present)
        item_columns = [col for col in df.columns if col in self.item_to_concept]
        logger.info(f"Found {len(item_columns)} item columns to aggregate")
        
        # Initialize aggregated dataframe
        aggregated_data = []
        
        for idx, row in df.iterrows():
            student_mastery = {}
            
            for concept in self.unique_concepts:
                # Get all items for this concept
                concept_items = [item for item in self.concept_to_items[concept] if item in item_columns]
                
                if not concept_items:
                    # No items for this concept in current data
                    student_mastery[concept] = 0.0
                    continue
                
                # Calculate mastery: mean of responses (handling NaN as 0)
                responses = row[concept_items].fillna(0).values
                mastery_score = np.mean(responses)
                student_mastery[concept] = mastery_score
            
            aggregated_data.append(student_mastery)
        
        # Create DataFrame
        aggregated_df = pd.DataFrame(aggregated_data)
        
        logger.info(f"Aggregated shape: {aggregated_df.shape[0]} students, {aggregated_df.shape[1]} concepts")
        logger.info(f"Mastery score range: [{aggregated_df.min().min():.3f}, {aggregated_df.max().max():.3f}]")
        
        # Statistics
        mean_mastery = aggregated_df.mean(axis=0).mean()
        logger.info(f"Mean mastery across all concepts: {mean_mastery:.3f}")
        
        # Save aggregated data
        aggregated_df.to_csv(output_file, index=False)
        logger.info(f"Saved aggregated data to {output_file}")
        
        # Also save concept mapping for later use
        mapping_file = output_file.parent / "concept_to_items_mapping.json"
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(self.concept_to_items, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved concept mapping to {mapping_file}")
        
        return aggregated_df, self.concept_to_items
    
    def binarize_concepts(
        self,
        aggregated_df: pd.DataFrame,
        threshold: float = 0.5
    ) -> pd.DataFrame:
        """
        Convert mastery scores to binary (0/1) based on threshold
        
        Args:
            aggregated_df: DataFrame with mastery scores
            threshold: Mastery threshold for considering concept "mastered"
            
        Returns:
            Binarized DataFrame
        """
        logger.info(f"Binarizing concepts with threshold={threshold}")
        
        binarized = (aggregated_df >= threshold).astype(int)
        
        mastered_counts = binarized.sum(axis=0)
        logger.info(f"Concepts mastered by >50% students: {(mastered_counts > len(binarized)/2).sum()}")
        
        return binarized
    
    def run_aggregation_pipeline(
        self,
        classifications_file: Path = None,
        data_file: Path = None,
        output_file: Path = None,
        binarize: bool = False,
        binarize_threshold: float = 0.5
    ) -> Path:
        """
        Complete aggregation pipeline
        
        Args:
            classifications_file: Path to LLM classifications
            data_file: Path to cleaned student data
            output_file: Path to save aggregated data
            binarize: Whether to binarize mastery scores
            binarize_threshold: Threshold for binarization
            
        Returns:
            Path to aggregated data file
        """
        # Use defaults from settings if not provided
        if classifications_file is None:
            classifications_file = settings.OUTPUT_DIR / "llm_item_classifications.json"
        if data_file is None:
            data_file = settings.CLEANED_DATA_FILE
        if output_file is None:
            output_file = settings.OUTPUT_DIR / "aggregated_concepts.csv"
        
        # Load classifications
        self.load_item_classifications(classifications_file)
        
        # Aggregate
        aggregated_df, concept_mapping = self.aggregate_to_concepts(data_file, output_file)
        
        # Optional binarization
        if binarize:
            binarized_df = self.binarize_concepts(aggregated_df, binarize_threshold)
            binarized_file = output_file.parent / "aggregated_concepts_binary.csv"
            binarized_df.to_csv(binarized_file, index=False)
            logger.info(f"Saved binarized data to {binarized_file}")
            return binarized_file
        
        return output_file


# Singleton instance
concept_aggregation_service = ConceptAggregationService()
