import argparse
import sys
import os
import torch

# Force CPU-only mode (no CUDA)
os.environ['CUDA_VISIBLE_DEVICES'] = ''
torch.cuda.is_available = lambda: False

from learning_space_generator.app.services.preprocessing_service import preprocessing_service
from learning_space_generator.app.services.structure_service import structure_service
from learning_space_generator.app.services.knowledge_space_service import knowledge_space_service
from learning_space_generator.app.services.visualization_service import visualization_service
from learning_space_generator.app.services.validation_service import validation_service
from learning_space_generator.app.services.ontology_service import ontology_service
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("SOTIS-App")

def main():
    parser = argparse.ArgumentParser(description="SOTIS 2026 Knowledge Space Construction Pipeline")
    parser.add_argument('step', choices=['all', 'preprocess', 'semantic', 'aggregate', 'difficulty', 'extract', 'generate', 'visualize', 'validate', 'enrich'], 
                        help="Step to run (or 'all')")
    
    args = parser.parse_args()
    
    if args.step in ['all', 'preprocess']:
        logger.info("=== STEP 1: Preprocessing ===")
        print("PROGRESS:15:DAE preprocessing...", flush=True)
        preprocessing_service.run_preprocessing()
        print("PROGRESS:20:DAE preprocessing completed", flush=True)
        
    if args.step in ['all', 'semantic']:
        logger.info("=== STEP 2: Semantic Clustering (LLM + Embeddings) ===")
        print("PROGRESS:25:LLM classification...", flush=True)
        from learning_space_generator.app.services.semantic_service import semantic_service
        semantic_service.run_semantic_classification()
        print("PROGRESS:35:Semantic clustering completed", flush=True)
    
    if args.step in ['all', 'aggregate']:
        logger.info("=== STEP 2.5: Concept Aggregation (Items → Concepts) ===")
        print("PROGRESS:45:Concept aggregation...", flush=True)
        from learning_space_generator.app.services.concept_aggregation_service import concept_aggregation_service
        from learning_space_generator.app.core.config import settings
        concept_aggregation_service.run_aggregation_pipeline(
            binarize=True,
            binarize_threshold=settings.CONCEPT_BINARIZE_THRESHOLD
        )
        print("PROGRESS:50:Concept aggregation completed", flush=True)
        logger.info("Concept aggregation completed. IITA will now run on concept-level data.")
    
    if args.step in ['all', 'difficulty']:
        logger.info("=== STEP 2.6: Difficulty Analysis (Sort Items by Difficulty) ===")
        print("PROGRESS:55:Difficulty analysis...", flush=True)
        from learning_space_generator.app.services.difficulty_service import DifficultyService
        difficulty_service = DifficultyService()
        difficulty_service.run_difficulty_analysis()
        print("PROGRESS:60:Difficulty analysis completed", flush=True)
        logger.info("Difficulty analysis completed. Items sorted within each concept.")
        
    if args.step in ['all', 'extract']:
        logger.info("=== STEP 3: Structure Extraction (Concept-Level IITA) ===")
        print("PROGRESS:65:IITA prerequisite extraction...", flush=True)
        structure_service.run_extraction()
        print("PROGRESS:70:IITA extraction completed", flush=True)
        
    if args.step in ['all', 'generate']:
        logger.info("=== STEP 4: Knowledge Space Generation ===")
        print("PROGRESS:75:Knowledge space generation...", flush=True)
        knowledge_space_service.generate_states()
        print("PROGRESS:80:Knowledge space generation completed", flush=True)
        
    if args.step in ['all', 'visualize']:
        logger.info("=== STEP 5: Visualization ===")
        print("PROGRESS:85:Visualization...", flush=True)
        visualization_service.generate_static_graph()
        print("PROGRESS:88:Visualization completed", flush=True)
        
    if args.step in ['all', 'validate']:
        logger.info("=== STEP 6: Validation ===")
        validation_service.validate_structure()
        validation_service.semantic_validation_check()
    
    if args.step in ['all', 'enrich']:
        logger.info("=== STEP 7: Ontology Export ===")
        print("PROGRESS:90:RDF/TTL ontology export...", flush=True)
        ontology_service.generate_ontology()
        print("PROGRESS:94:Ontology export completed", flush=True)

    print("PROGRESS:95:Finalizing...", flush=True)
    logger.info("Pipeline Execution Completed.")

if __name__ == "__main__":
    main()
