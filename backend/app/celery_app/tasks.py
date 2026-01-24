"""
Celery Tasks - Pokreće Learning Space Generator

Ovaj task je **most** između backend-a i learning_space_generator-a.
"""

import subprocess
import json
import shutil
from pathlib import Path
from datetime import datetime
from celery import Task
from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.task import Task as TaskModel
from app.models.result import Result
from app import models  # Ensure all tables registered in metadata
from app.config import settings


class DatabaseTask(Task):
    """Custom Celery task sa database session"""
    _db = None

    @property
    def db(self):
        if self._db is None:
            self._db = SessionLocal()
        return self._db


@celery_app.task(base=DatabaseTask, bind=True)
def run_learning_space_generator(self, task_id: int, upload_id: int, csv_path: str):
    """
    Pokreće learning_space_generator kao subproces i čuva rezultate u bazu
    
    Workflow:
    1. Kopiraj CSV u learning_space_generator/data/
    2. Pokreni learning_space_generator subprocess
    3. Parsiruj output i ažuriraj progress u bazi
    4. Sačekaj završetak
    5. Učitaj rezultate iz learning_space_generator/output/
    6. Sačuvaj rezultate u PostgreSQL
    """
    
    db = self.db
    
    try:
        # Pronađi task u bazi
        task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # Update task status
        task.status = "running"
        task.started_at = datetime.now()
        task.message = "Preparing data..."
        task.progress = 5
        db.commit()
        
        # Pripremi putanje
        lsg_path = Path(settings.LSG_PATH)
        lsg_data_path = lsg_path / "data"
        lsg_output_path = lsg_path / "output"
        
        # Kreiraj direktorijume ako ne postoje
        lsg_data_path.mkdir(parents=True, exist_ok=True)
        lsg_output_path.mkdir(parents=True, exist_ok=True)
        
        # Kopiraj CSV u LSG data folder
        csv_filename = "uploaded_data.csv"
        target_csv = lsg_data_path / csv_filename
        shutil.copy(csv_path, target_csv)
        
        task.message = "Starting Learning Space Generator..."
        task.progress = 10
        db.commit()
        
        # Pokreni learning_space_generator
        venv_python = lsg_path / ".venv" / "bin" / "python" if (lsg_path / ".venv" / "bin").exists() else "python"
        script = lsg_path / settings.LSG_SCRIPT
        
        process = subprocess.Popen(
            [str(venv_python), str(script), "all"],
            cwd=str(lsg_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Parsiranje output-a za progress - traži eksplicitne PROGRESS: markere
        for line in process.stdout:
            # Traži eksplicitan PROGRESS marker u formatu: PROGRESS:XX:Message
            if line.startswith("PROGRESS:"):
                try:
                    parts = line.strip().split(":", 2)
                    if len(parts) >= 3:
                        progress_value = int(parts[1])
                        progress_message = parts[2]
                        task.progress = progress_value
                        task.message = progress_message
                        db.commit()
                except (ValueError, IndexError):
                    pass  # Ignoriši loše formatirane progress linije
        
        # Sačekaj završetak
        return_code = process.wait()
        
        if return_code != 0:
            stderr_output = process.stderr.read() if process.stderr else "Unknown error"
            raise RuntimeError(f"Learning Space Generator failed: {stderr_output}")
        
        task.message = "Saving results to database..."
        task.progress = 95
        db.commit()
        
        # Učitaj rezultate iz output foldera
        statistics = {}
        result_files = {}
        knowledge_space_data = None
        implications_data = None
        semantic_clusters_data = None
        llm_classifications_data = None
        item_difficulties_data = None
        
        # Load statistics from JSON files
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
        
        # Pronađi root concepts (bez prerequisites)
        root_count = 0
        if knowledge_space_data and implications_data:
            for state in knowledge_space_data.keys():
                if state == "{}":  # Empty set je root
                    root_count += 1
            statistics["root_concepts"] = max(1, root_count)  # Minimum 1
        
        # Index all result files
        for file_path in lsg_output_path.glob("*"):
            if file_path.is_file():
                result_files[file_path.name] = str(file_path)
        
        # Sačuvaj rezultate u bazu
        result = Result(
            task_id=task_id,
            total_items=statistics.get("total_items", 0),
            total_concepts=statistics.get("total_concepts", 0),
            total_students=statistics.get("total_students", 0),
            knowledge_space_states=statistics.get("knowledge_space_states", 0),
            prerequisites_found=statistics.get("prerequisites_found", 0),
            semantic_clusters=statistics.get("semantic_clusters", 0),
            root_concepts=statistics.get("root_concepts", 0),
            # Sačuvaj JSON podatke u bazu
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
        
        # Označi task kao completed
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
        # Označi task kao failed
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

