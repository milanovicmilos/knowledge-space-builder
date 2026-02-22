"""Celery tasks that run the Learning Space Generator (LSG).

This module acts as the bridge between the backend and the LSG. It uses
direct Python imports of LSG services instead of subprocess execution to
improve performance and error handling.
"""

import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional
from celery import Task
from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.task import Task as TaskModel
from app.models.result import Result
from app import models  # Ensure all tables registered in metadata
from app.config import settings
import logging

# Setup logging
logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Custom Celery Task that provides a DB session."""
    _db = None

    @property
    def db(self):
        if self._db is None:
            self._db = SessionLocal()
        return self._db


@celery_app.task(base=DatabaseTask, bind=True)
def run_learning_space_generator(self, task_id: int, upload_id: int, csv_path: str, pdf_path: Optional[str] = None):
    """Run the Learning Space Generator pipeline via direct imports.

    Steps:
    1. Copy CSV (and optional PDF) into LSG `data/` directory
    2. Import LSG services directly
    3. Execute pipeline steps and track progress
    4. Load generated outputs from LSG `output/`
    5. Persist results into PostgreSQL
    """
    
    db = self.db
    
    try:
        # Find task in DB
        task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # Mark task as running
        task.status = "running"
        task.started_at = datetime.now()
        task.message = "Preparing data..."
        task.progress = 5
        db.commit()
        
        # Prepare LSG paths
        lsg_path = Path(settings.LSG_PATH)
        lsg_data_path = lsg_path / "data"
        lsg_output_path = lsg_path / "output"
        
        # Create directories if missing
        lsg_data_path.mkdir(parents=True, exist_ok=True)
        lsg_output_path.mkdir(parents=True, exist_ok=True)
        
        # Copy CSV into LSG data folder
        csv_filename = "uploaded_data.csv"
        target_csv = lsg_data_path / csv_filename
        shutil.copy(csv_path, target_csv)

        uploaded_pdf_target = lsg_data_path / "uploaded_tasks.pdf"
        if pdf_path:
            shutil.copy(pdf_path, uploaded_pdf_target)
        elif uploaded_pdf_target.exists():
            uploaded_pdf_target.unlink()
        
        task.message = "Initializing Learning Space Generator..."
        task.progress = 10
        db.commit()
        
        # Ensure LSG path is on sys.path for direct imports
        if str(lsg_path) not in sys.path:
            sys.path.insert(0, str(lsg_path))
        
        # Import LSG services via direct import
        try:
            from learning_space_generator.app.services.preprocessing_service import preprocessing_service
            from learning_space_generator.app.services.semantic_service import semantic_service
            from learning_space_generator.app.services.concept_aggregation_service import concept_aggregation_service
            from learning_space_generator.app.services.difficulty_service import DifficultyService
            from learning_space_generator.app.services.structure_service import structure_service
            from learning_space_generator.app.services.knowledge_space_service import knowledge_space_service
            from learning_space_generator.app.services.visualization_service import visualization_service
            from learning_space_generator.app.services.validation_service import validation_service
            from learning_space_generator.app.services.ontology_service import ontology_service
        except ImportError as e:
            logger.error(f"Failed to import LSG services: {e}")
            raise RuntimeError(f"Cannot import Learning Space Generator modules: {e}")
        
        # === STEP 1: Preprocessing ===
        logger.info("STEP 1: Preprocessing")
        task.message = "Preprocessing data..."
        task.progress = 15
        db.commit()
        
        preprocessing_service.run_preprocessing()
        
        task.progress = 20
        task.message = "Preprocessing completed"
        db.commit()
        
        # === STEP 2: Semantic Clustering ===
        logger.info("STEP 2: Semantic Clustering")
        task.message = "LLM classification and semantic clustering..."
        task.progress = 25
        db.commit()
        
        semantic_service.run_semantic_classification()
        
        task.progress = 35
        task.message = "Semantic clustering completed"
        db.commit()
        
        # === STEP 3: Concept Aggregation ===
        logger.info("STEP 3: Concept Aggregation")
        task.message = "Aggregating items into concepts..."
        task.progress = 45
        db.commit()
        
        concept_aggregation_service.run_aggregation_pipeline(
            binarize=True,
            binarize_threshold=None  # Uses settings.CONCEPT_BINARIZE_THRESHOLD by default
        )
        
        task.progress = 50
        task.message = "Concept aggregation completed"
        db.commit()
        
        # === STEP 4: Difficulty Analysis ===
        logger.info("STEP 4: Difficulty Analysis")
        task.message = "Analyzing item difficulties..."
        task.progress = 55
        db.commit()
        
        difficulty_service = DifficultyService()
        difficulty_service.run_difficulty_analysis()
        
        task.progress = 60
        task.message = "Difficulty analysis completed"
        db.commit()
        
        # === STEP 5: Structure Extraction (IITA) ===
        logger.info("STEP 5: Structure Extraction (IITA)")
        task.message = "Extracting prerequisite structure..."
        task.progress = 65
        db.commit()
        
        structure_service.run_extraction()
        
        task.progress = 70
        task.message = "Structure extraction completed"
        db.commit()
        
        # === STEP 6: Knowledge Space Generation ===
        logger.info("STEP 6: Knowledge Space Generation")
        task.message = "Generating knowledge space states..."
        task.progress = 75
        db.commit()
        
        knowledge_space_service.generate_states()
        
        task.progress = 80
        task.message = "Knowledge space generation completed"
        db.commit()
        
        # === STEP 7: Visualization ===
        logger.info("STEP 7: Visualization")
        task.message = "Generating visualizations..."
        task.progress = 85
        db.commit()
        
        visualization_service.generate_static_graph()
        
        task.progress = 88
        task.message = "Visualization completed"
        db.commit()
        
        # === STEP 8: Validation ===
        logger.info("STEP 8: Validation")
        validation_service.validate_structure()
        validation_service.semantic_validation_check()
        
        # === STEP 9: Ontology Export ===
        logger.info("STEP 9: Ontology Export")
        task.message = "Exporting RDF/TTL ontology..."
        task.progress = 90
        db.commit()
        
        ontology_service.generate_ontology()
        
        task.progress = 94
        task.message = "Ontology export completed"
        db.commit()
        
        # === Load and save results ===
        logger.info("Loading results from output folder...")
        task.message = "Saving results to database..."
        task.progress = 95
        db.commit()
        
        # Load results from output folder
        statistics = {}
        result_files = {}
        knowledge_space_data = None
        implications_data = None
        semantic_clusters_data = None
        llm_classifications_data = None
        item_difficulties_data = None
        
        # Load statistics from generated JSON files
        if (lsg_output_path / "llm_item_classifications.json").exists():
            with open(lsg_output_path / "llm_item_classifications.json", 'r') as f:
                llm_classifications_data = json.load(f)
                statistics["total_items"] = len(llm_classifications_data)
                statistics["total_concepts"] = len(set(llm_classifications_data.values()))
        
        if (lsg_output_path / "knowledge_space.json").exists():
            with open(lsg_output_path / "knowledge_space.json", 'r') as f:
                knowledge_space_data = json.load(f)
                statistics["knowledge_space_states"] = len(knowledge_space_data)
        
        if (lsg_output_path / "implications.json").exists():
            with open(lsg_output_path / "implications.json", 'r') as f:
                implications_data = json.load(f)
                statistics["prerequisites_found"] = len(implications_data)
        
        if (lsg_output_path / "semantic_clusters.json").exists():
            with open(lsg_output_path / "semantic_clusters.json", 'r') as f:
                semantic_clusters_data = json.load(f)
                statistics["semantic_clusters"] = len(semantic_clusters_data)
        
        if (lsg_output_path / "item_difficulties.json").exists():
            with open(lsg_output_path / "item_difficulties.json", 'r') as f:
                item_difficulties_data = json.load(f)
        
        if (lsg_output_path / "aggregated_concepts.csv").exists():
            with open(lsg_output_path / "aggregated_concepts.csv", 'r') as f:
                lines = f.readlines()
                if len(lines) > 1:
                    statistics["total_students"] = len(lines) - 1
        
        # Find root concepts (states with no prerequisites)
        root_count = 0
        if knowledge_space_data and implications_data:
            for state in knowledge_space_data.keys():
                if state == "{}":  # Empty set is a root
                    root_count += 1
            statistics["root_concepts"] = max(1, root_count)  # Minimum 1
        
        # Index all result files in output folder
        for file_path in lsg_output_path.glob("*"):
            if file_path.is_file():
                result_files[file_path.name] = str(file_path)
        
        # Persist results to DB
        result = Result(
            task_id=task_id,
            total_items=statistics.get("total_items", 0),
            total_concepts=statistics.get("total_concepts", 0),
            total_students=statistics.get("total_students", 0),
            knowledge_space_states=statistics.get("knowledge_space_states", 0),
            prerequisites_found=statistics.get("prerequisites_found", 0),
            semantic_clusters=statistics.get("semantic_clusters", 0),
            root_concepts=statistics.get("root_concepts", 0),
            # Store JSON data in DB
            knowledge_space=knowledge_space_data,
            implications=implications_data,
            semantic_clusters_data=semantic_clusters_data,
            llm_classifications=llm_classifications_data,
            item_difficulties=item_difficulties_data,
            # File references
            result_files=result_files,
            # Metadata
            source="web_app",
            storage_location="postgresql"
        )
        db.add(result)
        
        # Mark task as completed
        task.status = "completed"
        task.completed_at = datetime.now()
        task.progress = 100
        task.message = "Analysis completed successfully!"
        db.commit()
        
        return {
            "status": "success",
            "task_id": task_id,
            "statistics": statistics
        }
    
    except Exception as e:
        # Mark task as failed
        task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        if task:
            task.status = "failed"
            task.completed_at = datetime.now()
            task.error_message = str(e)
            task.message = f"Error: {str(e)}"
            db.commit()
        
        raise
    
    finally:
        db.close()

