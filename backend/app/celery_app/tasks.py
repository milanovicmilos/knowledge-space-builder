import sys
import os
import time
import json
import logging
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from app.celery_app import celery_app
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.task import Task as TaskModel
from app.models.upload import Upload
from app.models.result import Result
from app.services.storage import storage_service
from app.config import settings

# Import LSG Services from the actual algorithm package
from learning_space_generator.app.services.preprocessing_service import preprocessing_service
from learning_space_generator.app.services.structure_service import structure_service
from learning_space_generator.app.services.knowledge_space_service import knowledge_space_service
from learning_space_generator.app.services.visualization_service import visualization_service
from learning_space_generator.app.services.semantic_service import semantic_service
from learning_space_generator.app.services.ontology_service import ontology_service
from learning_space_generator.app.services.concept_aggregation_service import concept_aggregation_service

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def run_algorithm_task(self, task_id: int, upload_id: int, parameters: dict):
    db: Session = SessionLocal()
    
    try:
        # Load Task
        task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        if not task:
            logger.error(f"Task {task_id} not found")
            return

        task.status = "running"
        task.started_at = datetime.now(timezone.utc)
        task.progress_percent = 0
        task.progress_details = {"stage": "initializing", "progress_percent": 0}
        db.commit()
        
        # Load Upload
        upload = db.query(Upload).filter(Upload.id == upload_id).first()
        if not upload:
            raise ValueError(f"Upload {upload_id} not found")
            
        csv_path = storage_service.get_file_path(upload.storage_key)
        # Ensure path exists or resolve it relative to storage_path
        if not os.path.exists(csv_path):
             csv_path = str(Path(settings.STORAGE_PATH) / upload.storage_key)
             
        if not os.path.exists(csv_path):
             raise FileNotFoundError(f"CSV file not found at {csv_path}")

        # Setup Task Storage
        # usage: /app/storage/outputs/task_<id>/
        task_output_dir = Path(settings.OUTPUT_DIR) / f"task_{task_id}"
        task_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Define File Paths
        cleaned_file = task_output_dir / "cleaned.csv"
        implications_file = task_output_dir / "implications.json"
        knowledge_space_file = task_output_dir / "knowledge_space.json"
        graph_image_file = task_output_dir / "graph.png"
        semantic_clusters_file = task_output_dir / "semantic_clusters.json"
        ontology_file = task_output_dir / "sotis_ontology.ttl"
        
        # Override LSG settings with user-provided parameters
        from learning_space_generator.app.core.config import settings as lsg_settings
        
        # Extract parameters from request (with fallbacks to defaults)
        iita_threshold = parameters.get('iita_threshold', 0.05)
        semantic_weight = parameters.get('semantic_weight', 0.3)
        use_concept_level_iita = parameters.get('use_concept_level_iita', True)
        
        logger.info(f"User Parameters: IITA={iita_threshold}, Semantic Weight={semantic_weight}, Concept-Level={use_concept_level_iita}")
        
        # Override settings temporarily
        lsg_settings.IITA_THRESHOLD_RATE = iita_threshold
        lsg_settings.SEMANTIC_WEIGHT = semantic_weight
        lsg_settings.USE_CONCEPT_LEVEL_IITA = use_concept_level_iita
        lsg_settings.OUTPUT_DIR = task_output_dir
        lsg_settings.CLEANED_DATA_FILE = cleaned_file
        lsg_settings.IMPLICATIONS_FILE = implications_file
        lsg_settings.KNOWLEDGE_SPACE_FILE = knowledge_space_file
        lsg_settings.GRAPH_IMAGE_FILE = graph_image_file
        
        # Pipeline Execution
        try:
            # 1. Preprocessing
            self.update_state(state="PROGRESS", meta={"progress_percent": 10, "stage": "preprocessing"})
            task.progress_percent = 10
            task.progress_details = {"stage": "preprocessing", "detail": "Cleaning data & DAE"}
            db.commit()
            
            # Copy input CSV to LSG's expected location
            import shutil
            shutil.copy(csv_path, cleaned_file)
            logger.info(f"Input CSV copied to {cleaned_file} for LSG processing")
            
            # Run preprocessing (DAE denoising)
            preprocessing_service.run_preprocessing()
            
            # 2. Semantic Analysis
            self.update_state(state="PROGRESS", meta={"progress_percent": 25, "stage": "semantic"})
            task.progress_percent = 25
            task.progress_details = {"stage": "semantic", "detail": "Clustering Concepts"}
            db.commit()

            from learning_space_generator.app.services.semantic_service import semantic_service as lsg_semantic
            lsg_semantic.run_semantic_classification()
            
            # 2b. Concept Aggregation (NEW!) - only if concept-level IITA is enabled
            if use_concept_level_iita:
                self.update_state(state="PROGRESS", meta={"progress_percent": 35, "stage": "aggregation"})
                task.progress_percent = 35
                task.progress_details = {"stage": "aggregation", "detail": "Aggregating Items to Concepts"}
                db.commit()
                
                from learning_space_generator.app.services.concept_aggregation_service import concept_aggregation_service
                aggregated_file = concept_aggregation_service.run_aggregation_pipeline(
                    classifications_file=task_output_dir / "llm_item_classifications.json",
                    data_file=cleaned_file,
                    output_file=task_output_dir / "aggregated_concepts.csv",
                    binarize=True,  # Use binary mastery (>= 0.5 = mastered)
                    binarize_threshold=0.5
                )
                logger.info(f"Concept aggregation complete: {aggregated_file}")
            
            # 3. Structure Extraction (concept-level if enabled, otherwise item-level)
            self.update_state(state="PROGRESS", meta={"progress_percent": 40, "stage": "extraction"})
            task.progress_percent = 40
            task.progress_details = {"stage": "extraction", "detail": "Running IITA on Concepts"}
            db.commit()
            
            structure_service.run_extraction()
            
            # 4. Knowledge Space Generation
            self.update_state(state="PROGRESS", meta={"progress_percent": 60, "stage": "generation"})
            task.progress_percent = 60
            task.progress_details = {"stage": "generation", "detail": "Generating States"}
            db.commit()
            
            knowledge_space_service.generate_states()
            
            # 5. Visualization
            self.update_state(state="PROGRESS", meta={"progress_percent": 80, "stage": "visualization"})
            task.progress_percent = 80
            task.progress_details = {"stage": "visualization", "detail": "Creating Graph"}
            db.commit()
            
            visualization_service.generate_static_graph()

            # 6. Ontology Generation
            self.update_state(state="PROGRESS", meta={"progress_percent": 95, "stage": "ontology"})
            task.progress_details = {"stage": "ontology", "detail": "Exporting Ontology"}
            db.commit()

            ontology_service.generate_ontology()
            
            # Result Saving
            # Calculate num_states/edges
            with open(knowledge_space_file, "r") as f:
                ks = json.load(f)
                num_states = len(ks)
            
            with open(implications_file, "r") as f:
                imps = json.load(f)
                num_edges = len(imps)

            # Store result
            # We use knowledge_space.json as the main artifact key, but we can store others in metadata
            result = Result(
                task_id=task_id,
                graph_storage_key=str(knowledge_space_file.relative_to(Path(settings.STORAGE_PATH))), # Store relative path
                num_states=num_states,
                num_edges=num_edges,
                algorithm="lsg_pipeline",
                execution_time_seconds=int((datetime.now(timezone.utc) - task.started_at).total_seconds()),
                result_metadata={
                    "implications_file": str(implications_file.relative_to(Path(settings.STORAGE_PATH))),
                    "cleaned_file": str(cleaned_file.relative_to(Path(settings.STORAGE_PATH))),
                    "png_key": str(graph_image_file.relative_to(Path(settings.STORAGE_PATH))),
                    "ontology_file": str(ontology_file.relative_to(Path(settings.STORAGE_PATH))),
                    "semantic_clusters_file": str(semantic_clusters_file.relative_to(Path(settings.STORAGE_PATH)))
                }
            )
            db.add(result)
            
            task.status = "completed"
            task.completed_at = datetime.now(timezone.utc)
            task.progress_percent = 100
            task.progress_details = {"stage": "finished", "detail": "Done"}
            
            db.commit()
            
        except Exception as e:
            logger.exception("Task failed pipeline execution")
            raise e
            
    except Exception as e:
        logger.exception(f"Error in run_algorithm_task: {e}")
        task.status = "failed"
        task.error_message = str(e)
        task.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise e
    finally:
        db.close()

def parse_progress_line(line: str) -> Optional[Dict[str, Any]]:
    return None

